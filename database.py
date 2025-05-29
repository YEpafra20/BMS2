import mysql.connector
class DbTask:
    def creating_connecting(self):
        connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='YEpafra@20',
                database='BANK_DETAILS',
                auth_plugin='mysql_native_password'
            )
        return connection
    
obj2=DbTask()
obj2.creating_connecting()
