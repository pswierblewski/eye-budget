from abc import ABC
import os
import cv2
import numpy as np
from PIL import Image
from scipy.cluster.vq import kmeans, vq

class PreprocessingService(ABC):
    def __init__(self):
        self.input_dir = os.getenv("INPUT_DIR", "input/")
        self.output_dir = os.getenv("OUTPUT_DIR", "output/")
        self.sample_fraction = 5
        self.value_threshold = 0.25
        self.saturation_threshold = 0.2
        self.kmeans_iter = 40
        self.num_colors = 8
        self.white_bg = True
        self.saturate = True
        self.blur = True
        self.blur_kernel_size = (3, 3)

    def quantize(self, image, bits_per_channel):
        assert image.dtype == np.uint8
        shift = 8-bits_per_channel
        halfbin = (1 << shift) >> 1
        return ((image.astype(int) >> shift) << shift) + halfbin

    def pack_rgb(self, rgb):
        orig_shape = None
        if isinstance(rgb, np.ndarray):
            assert rgb.shape[-1] == 3
            orig_shape = rgb.shape[:-1]
        else:
            assert len(rgb) == 3
            rgb = np.array(rgb)

        rgb = rgb.astype(int).reshape((-1, 3))
        packed = (rgb[:, 0] << 16 |
                rgb[:, 1] << 8 |
                rgb[:, 2])

        if orig_shape is None:
            return packed
        else:
            return packed.reshape(orig_shape)

    def unpack_rgb(self, packed):
        orig_shape = None
        if isinstance(packed, np.ndarray):
            assert packed.dtype == int
            orig_shape = packed.shape
            packed = packed.reshape((-1, 1))

        rgb = ((packed >> 16) & 0xff,
            (packed >> 8) & 0xff,
            (packed) & 0xff)

        if orig_shape is None:
            return rgb
        else:
            return np.hstack(rgb).reshape(orig_shape + (3,))

    def get_bg_color(self, image, bits_per_channel):
        assert image.shape[-1] == 3
        quantized = self.quantize(image, bits_per_channel).astype(int)
        packed = self.pack_rgb(quantized)
        unique, counts = np.unique(packed, return_counts=True)
        packed_mode = unique[counts.argmax()]
        return self.unpack_rgb(packed_mode)

    def rgb_to_sv(self, rgb):
        if not isinstance(rgb, np.ndarray):
            rgb = np.array(rgb)

        axis = len(rgb.shape)-1
        cmax = rgb.max(axis=axis).astype(np.float32)
        cmin = rgb.min(axis=axis).astype(np.float32)
        delta = cmax - cmin
        saturation = delta.astype(np.float32) / cmax.astype(np.float32)
        saturation = np.where(cmax == 0, 0, saturation)
        value = cmax/255.0
        return saturation, value

    def load(self, img: Image):
        if img.mode != 'RGB':
            img = img.convert('RGB')
        if 'dpi' in img.info:
            dpi = img.info['dpi']
        else:
            dpi = (300, 300)
        dst = np.array(img)
        return dst, dpi

    def sample_pixels(self, img):
        pixels = img.reshape((-1, 3))
        num_pixels = pixels.shape[0]
        num_samples = int(num_pixels*self.sample_fraction)
        idx = np.arange(num_pixels)
        np.random.shuffle(idx)
        return pixels[idx[:num_samples]]

    def get_fg_mask(self, bg_color, samples):
        s_bg, v_bg = self.rgb_to_sv(bg_color)
        s_samples, v_samples = self.rgb_to_sv(samples)
        s_diff = np.abs(s_bg - s_samples)
        v_diff = np.abs(v_bg - v_samples)
        return ((v_diff >= self.value_threshold) |
                (s_diff >= self.saturation_threshold))

    def get_palette(self, samples):
        bg_color = self.get_bg_color(samples, 6)
        fg_mask = self.get_fg_mask(bg_color, samples)
        centers, _ = kmeans(samples[fg_mask].astype(np.float32), self.num_colors-1, iter=self.kmeans_iter)
        palette = np.vstack((bg_color, centers)).astype(np.uint8)
        return palette

    def apply_palette(self, img, palette):
        bg_color = palette[0]
        fg_mask = self.get_fg_mask(bg_color, img)
        orig_shape = img.shape
        pixels = img.reshape((-1, 3))
        fg_mask = fg_mask.flatten()
        num_pixels = pixels.shape[0]
        labels = np.zeros(num_pixels, dtype=np.uint8)
        labels[fg_mask], _ = vq(pixels[fg_mask], palette)
        return labels.reshape(orig_shape[:-1])

    def save(self, output_filename, labels, palette, dpi):
        if self.saturate:
            palette = palette.astype(np.float32)
            pmin = palette.min()
            pmax = palette.max()
            palette = 255 * (palette - pmin)/(pmax-pmin)
            palette = palette.astype(np.uint8)
        
        if self.white_bg:
            palette = palette.copy()
            palette[0] = (255, 255, 255)
        output_img = Image.fromarray(labels, 'P')
        output_img.putpalette(palette.flatten())
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdirname:
            output_img.save(f'{tmpdirname}/{output_filename}', dpi=dpi)
            output_img = cv2.imread(f'{tmpdirname}/{output_filename}')

        output_img = cv2.cvtColor(output_img, cv2.COLOR_RGB2GRAY)
        _, output_img = cv2.threshold(output_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if self.blur:
            output_img = cv2.GaussianBlur(output_img, self.blur_kernel_size, 0)
        return output_img

    def resize(self, input_img, scale_factor=0.5):
        new_size = (int(input_img.width * scale_factor), int(input_img.height * scale_factor))
        return input_img.resize(new_size)
    
    def preprocess(self, input_image_file):
        input_image_path = os.path.join(self.input_dir, input_image_file)
        input_img = Image.open(input_image_path)
        resized_img = self.resize(input_img)
        img, dpi = self.load(resized_img)
        import time
        timestr = time.strftime("%Y%m%d-%H%M%S")
        output_filename = f'{timestr}.png'

        samples = self.sample_pixels(img)
        palette = self.get_palette(samples)
        labels = self.apply_palette(img, palette)
        result = self.save(output_filename, labels, palette, dpi)
        output_filepath = os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_filepath, result)
        return output_filepath