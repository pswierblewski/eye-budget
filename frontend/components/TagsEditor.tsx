"use client";

import React, { useState, useRef, KeyboardEvent } from "react";
import { X } from "lucide-react";

interface TagsEditorProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  allTags?: string[];
  disabled?: boolean;
  placeholder?: string;
}

const DATALIST_ID = "tags-datalist";

export default function TagsEditor({
  tags,
  onChange,
  allTags = [],
  disabled = false,
  placeholder = "Dodaj tag…",
}: TagsEditorProps) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const addTag = (raw: string) => {
    const value = raw.trim().toLowerCase();
    if (!value) return;
    if (!tags.includes(value)) {
      onChange([...tags, value]);
    }
    setInput("");
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(input);
    } else if (e.key === "Backspace" && input === "" && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    }
  };

  const handleBlur = () => {
    if (input.trim()) addTag(input);
  };

  const suggestions = allTags.filter((t) => !tags.includes(t));

  return (
    <div
      className="flex flex-wrap gap-1.5 p-2 border border-gray-200 rounded-lg bg-white min-h-[2.5rem] cursor-text focus-within:ring-2 focus-within:ring-indigo-300 focus-within:border-indigo-400"
      onClick={() => inputRef.current?.focus()}
    >
      {suggestions.length > 0 && (
        <datalist id={DATALIST_ID}>
          {suggestions.map((t) => (
            <option key={t} value={t} />
          ))}
        </datalist>
      )}

      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full text-xs px-2 py-0.5 font-medium"
        >
          {tag}
          {!disabled && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); removeTag(tag); }}
              className="text-indigo-400 hover:text-indigo-700 leading-none"
              aria-label={`Usuń tag ${tag}`}
            >
              <X size={10} />
            </button>
          )}
        </span>
      ))}

      {!disabled && (
        <input
          ref={inputRef}
          type="text"
          list={suggestions.length > 0 ? DATALIST_ID : undefined}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder={tags.length === 0 ? placeholder : ""}
          className="flex-1 min-w-[120px] text-xs outline-none bg-transparent text-gray-700 placeholder-gray-400"
        />
      )}
    </div>
  );
}
