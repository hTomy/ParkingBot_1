import psycopg2

if __name__ == '__main__':

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname="parking_db",
        user="user",
        password="password",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parking_entries (
            id SERIAL PRIMARY KEY,
            license_plate VARCHAR(20),
            entry_time TIMESTAMP,
            spot_number INT
        );
    """)

    # Insert sample data
    cur.execute("""
        INSERT INTO parking_entries (license_plate, entry_time, spot_number)
        VALUES (%s, NOW(), %s)
        RETURNING id;
    """, ("ABC123", 42))

    # Get the inserted row's ID
    inserted_id = cur.fetchone()[0]
    print(f"Inserted parking_entries record with ID: {inserted_id}")

    # Commit and close
    conn.commit()
    cur.close()
    conn.close()