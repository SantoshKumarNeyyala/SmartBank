from database.connection import DatabaseConnection


class TransactionModel:

    @staticmethod
    def create_transaction(user_id, transaction_type, amount, previous_balance, new_balance):
        try:
            conn = DatabaseConnection.get_connection()
            cursor = conn.cursor()

            query = """
                INSERT INTO transactions 
                (user_id, transaction_type, amount, previous_balance, new_balance)
                VALUES (?, ?, ?, ?, ?)
            """

            cursor.execute(query, (
                user_id,
                transaction_type,
                amount,
                previous_balance,
                new_balance
            ))

            conn.commit()
            cursor.close()
            conn.close()

            return True

        except Exception as e:
            print("Transaction Error:", e)
            return False