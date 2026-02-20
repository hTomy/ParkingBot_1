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
        CREATE TABLE IF NOT EXISTS parking_bookings (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            license_plate VARCHAR(20),
            start_datetime TIMESTAMP,
            end_datetime TIMESTAMP,
            spot_number INT
        );
    """)

    # Insert sample data
    cur.execute("""
        INSERT INTO parking_bookings (name, license_plate, start_datetime, end_datetime, spot_number)
        VALUES
            ('Alice Smith', 'ABC123', '2026-02-17 08:00:00', '2026-02-17 10:00:00', 1),
            ('Bob Johnson', 'XYZ789', '2026-02-17 09:30:00', '2026-02-17 12:00:00', 2),
            ('Carol Lee', 'LMN456', '2026-02-17 11:00:00', '2026-02-17 13:30:00', 3),
            ('David Kim', 'JKL321', '2026-02-17 14:00:00', '2026-02-17 16:00:00', 4),
            ('Eva Brown', 'DEF654', '2026-02-17 15:30:00', '2026-02-17 17:00:00', 5),
            ('Frank Green', 'GHI987', '2026-02-18 07:00:00', '2026-02-18 09:00:00', 1),
            ('Grace White', 'QRS852', '2026-02-18 10:00:00', '2026-02-18 12:30:00', 2),
            ('Henry Black', 'TUV963', '2026-02-18 13:00:00', '2026-02-18 15:00:00', 3),
            ('Ivy Young', 'WXY741', '2026-02-18 16:00:00', '2026-02-18 18:00:00', 4),
            ('Jack King', 'ZAB159', '2026-02-18 19:00:00', '2026-02-19 21:00:00', 5);
    """)

    # Commit and close
    conn.commit()
    cur.close()
    conn.close()