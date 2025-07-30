class Config:
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root@localhost/kayzonale_db"
    JWT_SECRET_KEY = 'admin'
    SUPER_KEY = 'superAdmin123'
    JWT_TOKEN_LOCATION ='headers'
    PROPAGATE_EXCEPTIONS= 'True' # This allows Flask to propagate exceptions to the error handlers
    JWT_ERROR_MESSAGE_KEY = 'message' # This is the key used to return error messages in JWT responses
      # must match the one used to create the token

   
    DEBUG = True
    ENV = 'development'
