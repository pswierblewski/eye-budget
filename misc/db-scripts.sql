-- Create the enum type for status
CREATE TYPE receipt_status AS ENUM ('new', 'processing', 'processed', 'failed');

alter type receipt_status add value 'to_confirm';
alter type receipt_status add value 'done';

-- Create the table with quoted name
CREATE TABLE "receipts-scans" (
    id SERIAL PRIMARY KEY,
    filename VARCHAR NOT null UNIQUE,
    status receipt_status NOT NULL DEFAULT 'new',
    result JSONB
);

ALTER TABLE "receipts-scans" ADD CONSTRAINT filename UNIQUE (filename);

ALTER TABLE "receipts-scans" add categories_candidates varchar[];
ALTER TABLE "receipts-scans" drop categories_candidates;
ALTER TABLE "receipts-scans" add categories_candidates jsonb;
ALTER TABLE "receipts-scans" add category varchar;

CREATE TYPE category_type AS ENUM ('expense', 'income');

CREATE TABLE category_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    category_group_id INTEGER NOT NULL REFERENCES category_groups(id),
    name VARCHAR(255) NOT null,
    c_type category_type NOT NULL DEFAULT 'expense'
);

CREATE OR REPLACE FUNCTION insert_category(
    parent_name TEXT,
    category_name TEXT,
    group_name TEXT,
    ctype category_type DEFAULT 'expense'
) RETURNS VOID AS $$
DECLARE
    group_id INT;
    parent_id_int INT;
BEGIN
    SELECT id INTO group_id FROM category_groups WHERE name = group_name;
    IF group_id IS NULL THEN
        INSERT INTO category_groups (name) VALUES (group_name)
        RETURNING id INTO group_id;
    END IF;
    IF parent_name IS NOT NULL THEN
        SELECT id INTO parent_id_int FROM categories 
        WHERE name = parent_name AND parent_id IS NULL;
    ELSE
        parent_id_int := NULL;
    END IF;

    INSERT INTO categories (parent_id, category_group_id, name, c_type)
    VALUES (parent_id_int, group_id, category_name, ctype);
END;
$$ LANGUAGE plpgsql;

INSERT INTO category_groups (name) VALUES
('Bank Charges'),
('Other Expense'),
('Household Expenses'),
('Childcare Expenses'),
('Education'),
('Grocery Costs'),
('Entertainment'),
('Charitable Donations'),
('Other Bills'),
('Other Tax Payments'),
('Clothing Expenses');

DO $$
BEGIN
    -- Kategorie główne
    PERFORM insert_category(NULL, 'Bank opłaty', 'Bank Charges');
    PERFORM insert_category(NULL, 'Decha', 'Other Expense');
    PERFORM insert_category(NULL, 'Dieta', 'Other Expense');
    PERFORM insert_category(NULL, 'Dom', 'Household Expenses');
    PERFORM insert_category(NULL, 'Dzieciaki', 'Childcare Expenses');
    PERFORM insert_category(NULL, 'Dziecko', 'Other Expense');
    PERFORM insert_category(NULL, 'Edukacja', 'Education');
    PERFORM insert_category(NULL, 'Fryzjer', 'Other Expense');
    PERFORM insert_category(NULL, 'IKE', 'Other Expense');
    PERFORM insert_category(NULL, 'Inne', 'Other Expense');
    PERFORM insert_category(NULL, 'Jedzenie', 'Grocery Costs');
    PERFORM insert_category(NULL, 'Kosmetyczka', 'Other Expense');
    PERFORM insert_category(NULL, 'Kosmetyki', 'Other Expense');
    PERFORM insert_category(NULL, 'Księgowość', 'Other Expense');
    PERFORM insert_category(NULL, 'Napiwki', 'Other Expense');
    PERFORM insert_category(NULL, 'Podatki', 'Other Tax Payments');
    PERFORM insert_category(NULL, 'Podróże', 'Entertainment');
    PERFORM insert_category(NULL, 'Prezenty', 'Charitable Donations');
    PERFORM insert_category(NULL, 'Przesyłki i poczta', 'Other Expense');
    PERFORM insert_category(NULL, 'Rachunki', 'Other Bills');

    -- Podkategorie dla 'Dom'
    PERFORM insert_category('Dom', 'Elektronika', 'Household Expenses');
    PERFORM insert_category('Dom', 'Projekty', 'Household Expenses');
    PERFORM insert_category('Dom', 'Remonty', 'Household Expenses');
    PERFORM insert_category('Dom', 'Środki czystości i chemia', 'Household Expenses');
    PERFORM insert_category('Dom', 'Ubezpieczenie', 'Household Expenses');
    PERFORM insert_category('Dom', 'Wyposażenie', 'Household Expenses');

    -- Podkategorie dla 'Dzieciaki'
    PERFORM insert_category('Dzieciaki', 'Badania', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Inne', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Jedzenie', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Kosmetyki', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Leki', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Pieluchy', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Prezenty', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Środki czystości', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Szczepienia', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Ubrania', 'Clothing Expenses');
    PERFORM insert_category('Dzieciaki', 'Wyposażenie', 'Childcare Expenses');
    PERFORM insert_category('Dzieciaki', 'Zabawki', 'Childcare Expenses');

    -- Podkategorie dla 'Edukacja'
    PERFORM insert_category('Edukacja', 'Książki', 'Education');
    PERFORM insert_category('Edukacja', 'Opłaty', 'Education');

    -- Podkategorie dla 'Jedzenie'
    PERFORM insert_category('Jedzenie', 'Alkohol dom', 'Grocery Costs');
    PERFORM insert_category('Jedzenie', 'Alkohol miasto', 'Grocery Costs');
    PERFORM insert_category('Jedzenie', 'Jedzenie dom', 'Grocery Costs');
    PERFORM insert_category('Jedzenie', 'Jedzenie miasto', 'Grocery Costs');
    PERFORM insert_category('Jedzenie', 'Kawa', 'Grocery Costs');
    PERFORM insert_category('Jedzenie', 'Woda', 'Grocery Costs');

    -- Podkategorie dla 'Podróże' (z dodaną "Wycieczki")
    PERFORM insert_category('Podróże', 'Noclegi', 'Entertainment');
    PERFORM insert_category('Podróże', 'Wycieczki', 'Entertainment');
    
    PERFORM insert_category('Rachunki', 'Czynsz', 'Other Expense');
	PERFORM insert_category('Rachunki', 'Gaz', 'Other Bills');
	PERFORM insert_category('Rachunki', 'Hipoteka', 'Real Estate Taxes');
	PERFORM insert_category('Rachunki', 'Inne', 'Other Bills');
	PERFORM insert_category('Rachunki', 'Internet', 'Other Bills');
	PERFORM insert_category('Rachunki', 'Konta premium, licencje', 'Other Bills');
	PERFORM insert_category('Rachunki', 'Ogrzewanie', 'Other Bills');
	PERFORM insert_category('Rachunki', 'Prąd', 'Gas & Electric Bill');
	PERFORM insert_category('Rachunki', 'Śmieci', 'Other Bills');
	PERFORM insert_category('Rachunki', 'Telefon Ada', 'Telephone Bill');
	PERFORM insert_category('Rachunki', 'Telefon Paweł', 'Telephone Bill');
	PERFORM insert_category('Rachunki', 'Telefony', 'Other Bills');
	PERFORM insert_category('Rachunki', 'Telewizja', 'Cable Bill');
	PERFORM insert_category('Rachunki', 'Woda', 'Water & Sewer Bill');
	PERFORM insert_category('Rachunki', 'Wynajęm', 'Other Bills');
	
	-- Pozostałe kategorie główne
	PERFORM insert_category(NULL, 'Reklamówki', 'Other Expense');
	PERFORM insert_category(NULL, 'Rozrywka', 'Entertainment');
	PERFORM insert_category(NULL, 'Spłata pożyczek', 'Other Expense');
	PERFORM insert_category(NULL, 'Sport', 'Other Expense');
	
	-- Kategoria Transport z podkategoriami
	PERFORM insert_category(NULL, 'Transport', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Autostrady', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Honda opłaty', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Honda paliwo', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Honda serwis', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Honda wyposażenie', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Inne', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Kia Eksploatacja', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Kia Paliwo', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Kia serwis', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Kia Wyposażenie', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Komunikacja miejska', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Mandaty', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Mazda leasing', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Mazda paliwo', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Mazda serwis', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Mazda Ubezpieczenie', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Mazda wyposażenie', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Megane opłaty', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Megane paliwo', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Megane serwis', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Megane wyposażenie', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Paliwo', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Parkingi', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Pociągi', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Samoloty', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Taxi', 'Automobile Expenses');
	PERFORM insert_category('Transport', 'Zakup auta', 'Automobile Expenses');
	
	PERFORM insert_category(NULL, 'Ubrania, dodatki, inne', 'Clothing Expenses');
	PERFORM insert_category(NULL, 'Urzędowe sprawy', 'Other Expense');
	PERFORM insert_category(NULL, 'Usługi', 'Other Expense');
	PERFORM insert_category(NULL, 'Waluty', 'Other Expense');
	PERFORM insert_category(NULL, 'Wydarzenia', 'Other Expense');
	PERFORM insert_category(NULL, 'Wypłaty z bankomatów', 'Cash Withdrawal');
	
	-- Kategoria Zdrowie z podkategoriami
	PERFORM insert_category(NULL, 'Zdrowie', 'Medical/Dental Expenses');
	PERFORM insert_category('Zdrowie', 'Badania', 'Medical/Dental Expenses');
	PERFORM insert_category('Zdrowie', 'Dentysta', 'Medical/Dental Expenses');
	PERFORM insert_category('Zdrowie', 'Laryngolog', 'Medical/Dental Expenses');
	PERFORM insert_category('Zdrowie', 'Leki', 'Medical/Dental Expenses');
	PERFORM insert_category('Zdrowie', 'Okulista', 'Medical/Dental Expenses');
	PERFORM insert_category('Zdrowie', 'Szpital', 'Medical/Dental Expenses');
	PERFORM insert_category('Zdrowie', 'Ubezpieczenie', 'Medical/Dental Expenses');
	
	-- Kategoria Zwierzęta z podkategoriami
	PERFORM insert_category(NULL, 'Zwierzęta', 'Other Expense');
	PERFORM insert_category('Zwierzęta', 'Inne', 'Other Expense');
	PERFORM insert_category('Zwierzęta', 'Jedzenie', 'Other Expense');
	PERFORM insert_category('Zwierzęta', 'Usługi', 'Other Expense');
	PERFORM insert_category('Zwierzęta', 'Weterynarz', 'Other Expense');
	PERFORM insert_category('Zwierzęta', 'Wyposażenie', 'Other Expense');
	PERFORM insert_category('Zwierzęta', 'Żwirek', 'Other Expense');
	
	-- Kategorie INCOME
	PERFORM insert_category(NULL, 'Dodatki z pracy', 'Other Income', 'income');
	
	-- Kategoria Inne zyski z podkategoriami
	PERFORM insert_category(NULL, 'Inne zyski', 'Other Income', 'income');
	PERFORM insert_category('Inne zyski', 'Employee Stock Option', 'Periodic Income', 'income');
	PERFORM insert_category('Inne zyski', 'Loterie', 'Other Income', 'income');
	PERFORM insert_category('Inne zyski', 'Prezenty', 'Gifts Received', 'income');
	PERFORM insert_category('Inne zyski', 'Zwroty podatków', 'State/Local Tax Refund', 'income');
	PERFORM insert_category('Inne zyski', 'Zwroty pożyczek', 'Tax-Exempt Income', 'income');
	
	-- Kategoria Inwestycje z podkategoriami
	PERFORM insert_category(NULL, 'Inwestycje', 'Interest & Dividends', 'income');
	PERFORM insert_category('Inwestycje', 'Dywidendy', 'Interest & Dividends', 'income');
	PERFORM insert_category('Inwestycje', 'Odsetki', 'Interest & Dividends', 'income');
	PERFORM insert_category('Inwestycje', 'Tax-Exempt Interest', 'Tax-Exempt Income', 'income');
	PERFORM insert_category('Inwestycje', 'Zyski kapitałowe', 'Interest & Dividends', 'income');
	
	-- Pozostałe kategorie INCOME
	PERFORM insert_category(NULL, 'Nie wydatek', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Pensja Ada', 'Salary Income', 'income');
	PERFORM insert_category(NULL, 'Pensja Paweł', 'Salary Income', 'income');
	PERFORM insert_category(NULL, 'Pożyczki', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Premia Ada', 'Salary Income', 'income');
	PERFORM insert_category(NULL, 'Premia Paweł', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Projekty', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Przysługi', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Socjalne', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Sprzedaż rzeczy', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Ubezpieczenie', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Zwroty rzeczy', 'Other Income', 'income');
	PERFORM insert_category(NULL, 'Zwroty zakupów', 'Other Income', 'income');
end; $$ LANGUAGE plpgsql;

select c.id, c."name" as "category_name", cp."name" as "category_parent_name", cg."name" as "category_group_name", c.c_type as "category_type"
from categories c
left join categories cp on cp.id = c.parent_id
left join category_groups cg on cg.id = c.category_group_id