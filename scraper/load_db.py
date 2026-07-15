"""
Load all JSONL data into a DuckDB database for fast SQL querying.
Re-running this recreates the DB from the source files.
"""

import duckdb
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "laplata.duckdb"

def main():
    db = duckdb.connect(str(DB_PATH))

    db.execute("DROP TABLE IF EXISTS records")
    db.execute("DROP TABLE IF EXISTS adjudicaciones")
    db.execute("DROP TABLE IF EXISTS inmuebles")

    # Main records table
    db.execute(f"""
        CREATE TABLE records AS
        SELECT * FROM read_ndjson('{DATA_DIR}/records.jsonl',
            columns = {{
                bulletin_id:      'INTEGER',
                bulletin_display: 'INTEGER',
                bulletin_date:    'VARCHAR',
                doc_type:         'VARCHAR',
                doc_number:       'VARCHAR',
                doc_date:         'VARCHAR',
                expediente:       'VARCHAR',
                tags:             'VARCHAR[]',
                is_extractada:    'BOOLEAN',
                amounts:          'VARCHAR[]',
                text:             'VARCHAR',
                text_length:      'INTEGER'
            }}
        )
    """)

    # Add year/month columns
    db.execute("""
        ALTER TABLE records ADD COLUMN year INTEGER;
        ALTER TABLE records ADD COLUMN month INTEGER;
        UPDATE records SET
            year  = CAST(split_part(bulletin_date, '/', 3) AS INTEGER),
            month = CAST(split_part(bulletin_date, '/', 2) AS INTEGER)
        WHERE bulletin_date LIKE '%/%/%'
    """)

    # Adjudicaciones table
    db.execute(f"""
        CREATE TABLE adjudicaciones AS
        SELECT * FROM read_ndjson('{DATA_DIR}/adjudicaciones.jsonl',
            columns = {{
                bulletin_id:      'INTEGER',
                bulletin_date:    'VARCHAR',
                year:             'INTEGER',
                month:            'INTEGER',
                doc_number:       'VARCHAR',
                doc_date:         'VARCHAR',
                expediente:       'VARCHAR',
                contract_type:    'VARCHAR',
                contract_number:  'VARCHAR',
                bidders:          'VARCHAR[]',
                winner:           'VARCHAR',
                all_amounts:      'DOUBLE[]',
                awarded_amount:   'DOUBLE',
                n_bidders:        'INTEGER',
                description:      'VARCHAR',
                text_snippet:     'VARCHAR'
            }}
        )
    """)

    # Inmuebles table
    db.execute(f"""
        CREATE TABLE inmuebles AS
        SELECT * FROM read_ndjson('{DATA_DIR}/inmuebles.jsonl',
            columns = {{
                bulletin_id:     'INTEGER',
                bulletin_date:   'VARCHAR',
                year:            'INTEGER',
                doc_number:      'VARCHAR',
                doc_date:        'VARCHAR',
                operations:      'VARCHAR[]',
                parcela:         'VARCHAR',
                circunscripcion: 'VARCHAR',
                seccion:         'VARCHAR',
                amounts:         'DOUBLE[]',
                beneficiario:    'VARCHAR',
                direccion:       'VARCHAR',
                text_snippet:    'VARCHAR'
            }}
        )
    """)

    print("Tables created:")
    for t in ["records", "adjudicaciones", "inmuebles"]:
        n = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n:,} rows")

    db.close()
    print(f"\nDatabase: {DB_PATH}")

if __name__ == "__main__":
    main()
