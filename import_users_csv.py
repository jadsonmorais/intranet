import csv
import sqlite3
from pathlib import Path

DB_PATH = Path("instance/intranet_carmel.db")
CSV_PATH = Path("usuarios.csv")  # seu arquivo

EMAIL_KEYS = {"email", "e-mail", "mail", "usuario", "usuário", "login"}
SETOR_KEYS = {"setor", "sector", "departamento", "area", "área"}

def norm_key(s: str) -> str:
    return (s or "").strip().lower()

def norm_val(s: str) -> str:
    return (s or "").strip()

def find_column(fieldnames, accepted_keys):
    if not fieldnames:
        return None
    for col in fieldnames:
        if norm_key(col) in accepted_keys:
            return col
    return None

def detect_dialect(file_obj):
    """
    Detecta automaticamente se é ; , ou TAB.
    """
    sample = file_obj.read(4096)
    file_obj.seek(0)

    # tenta sniff
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        return dialect
    except Exception:
        # fallback: tenta adivinhar pelo cabeçalho
        first_line = sample.splitlines()[0] if sample else ""
        if ";" in first_line:
            class D(csv.excel):
                delimiter = ";"
            return D()
        if "\t" in first_line:
            class D(csv.excel_tab):
                delimiter = "\t"
            return D()
        return csv.excel  # vírgula

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Banco não encontrado: {DB_PATH.resolve()}")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV não encontrado: {CSV_PATH.resolve()}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    created = 0
    updated = 0
    skipped = 0
    invalid = 0

    with open(CSV_PATH, "r", newline="", encoding="utf-8-sig") as f:
        dialect = detect_dialect(f)
        reader = csv.DictReader(f, dialect=dialect)

        # ✅ agora fieldnames vai virar ['EMAIL', 'SETOR'] certinho
        email_col = find_column(reader.fieldnames, EMAIL_KEYS)
        setor_col = find_column(reader.fieldnames, SETOR_KEYS)

        if not email_col:
            raise ValueError(
                f"CSV não possui coluna de EMAIL. Cabeçalhos encontrados: {reader.fieldnames}"
            )

        if not setor_col:
            print("⚠️ CSV não possui coluna de SETOR. Vou apenas criar usuários sem setor.")

        for row in reader:
            email = norm_val(row.get(email_col)).lower()
            setor = norm_val(row.get(setor_col)) if setor_col else ""

            if not email or "@" not in email:
                invalid += 1
                continue

            cur.execute("SELECT id, sector FROM user WHERE email = ?", (email,))
            existing = cur.fetchone()

            if existing:
                user_id, current_sector = existing

                # ✅ Só atualiza setor se CSV trouxer setor preenchido
                if setor:
                    cur.execute("UPDATE user SET sector = ? WHERE id = ?", (setor, user_id))
                    updated += 1
                else:
                    skipped += 1
            else:
                cur.execute(
                    """
                    INSERT INTO user (email, name, sector, active, is_admin)
                    VALUES (?, '', ?, 1, 0)
                    """,
                    (email, setor if setor else None)
                )
                created += 1

    conn.commit()
    conn.close()

    print("IMPORTAÇÃO FINALIZADA")
    print(f"Usuários criados: {created}")
    print(f"Setores atualizados: {updated}")
    print(f"Ignorados (sem setor): {skipped}")
    print(f"Inválidos/sem email: {invalid}")

if __name__ == "__main__":
    main()
