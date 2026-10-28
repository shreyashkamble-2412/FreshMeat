
import mysql.connector
from werkzeug.security import generate_password_hash
from config import DB_CONFIG

username = "admin"
password = "Admin@123"

connection = None
cursor = None

try:
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    password_hash = generate_password_hash(password)

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, role)
        VALUES (%s, %s, 'admin')
        ON DUPLICATE KEY UPDATE
            password_hash = VALUES(password_hash),
            role = 'admin'
        """,
        (username, password_hash)
    )

    connection.commit()
    print("Admin account created successfully!")
    print("Username: admin")
    print("Password: Admin@123")

except mysql.connector.Error as error:
    print("MySQL Error:", error)

finally:
    if cursor is not None:
        cursor.close()
    if connection is not None and connection.is_connected():
        connection.close()
