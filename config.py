import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root@localhost/kayzonale_db"
    JWT_SECRET_KEY = 'admin'
    SUPER_KEY = 'superAdmin123'
    JWT_TOKEN_LOCATION ='headers'
    PROPAGATE_EXCEPTIONS= 'True' # This allows Flask to propagate exceptions to the error handlers
    JWT_ERROR_MESSAGE_KEY = 'message' # This is the key used to return error messages in JWT responses
      # must match the one used to create the token
      
#limit incoming request body (including file ) to e.g 5mb if thats your desired cap
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024 

# where uploads are stored on disk
    UPLOAD_FOLDER = os.path.join(basedir,'static', 'uploads','products') 
  
  
    DEBUG = True
    ENV = 'development'
