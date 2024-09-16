from passlib.context import CryptContext
import databases
import sqlalchemy as SQLAlchemy
from storeapi.config import config

# Initialize CryptContext with bcrypt hashing scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# metadata variable stores information about the database table and columns etc.
metadata = SQLAlchemy.MetaData()

campaign_table = SQLAlchemy.Table(
    "campaigns",
    metadata,
    SQLAlchemy.Column("id", SQLAlchemy.Integer, primary_key=True),
    SQLAlchemy.Column("name", SQLAlchemy.String(250)),
    SQLAlchemy.Column("template", SQLAlchemy.String(250)),
    SQLAlchemy.Column("isDraft", SQLAlchemy.Boolean, default=True),
    SQLAlchemy.Column("isPublished", SQLAlchemy.Boolean, default=False),
    SQLAlchemy.Column("isEnded", SQLAlchemy.Boolean, default=False),
)

users = SQLAlchemy.Table(
    "users",
    metadata,
    SQLAlchemy.Column("id", SQLAlchemy.Integer, primary_key=True),
    SQLAlchemy.Column("username", SQLAlchemy.String(50), unique=True, index=True),
    SQLAlchemy.Column("email", SQLAlchemy.String(100), unique=True, index=True),
    SQLAlchemy.Column("hashed_password", SQLAlchemy.String(100)),
)

# Define the payments table
payments = SQLAlchemy.Table(
    "payments",
    metadata,
    SQLAlchemy.Column("id", SQLAlchemy.Integer, primary_key=True),
    SQLAlchemy.Column("user_id", SQLAlchemy.Integer, SQLAlchemy.ForeignKey("users.id")),  # Link to the user
    SQLAlchemy.Column("amount", SQLAlchemy.Float),
    SQLAlchemy.Column("status", SQLAlchemy.String(50)),  # "success" or "failed"
    SQLAlchemy.Column("payment_method", SQLAlchemy.String(50)),
    SQLAlchemy.Column("created_at", SQLAlchemy.DateTime, default=SQLAlchemy.func.now())
)

refund_requests = SQLAlchemy.Table(
    "refund_requests",
    metadata,
    SQLAlchemy.Column("id", SQLAlchemy.Integer, primary_key=True),
    SQLAlchemy.Column("user_id", SQLAlchemy.Integer, SQLAlchemy.ForeignKey("users.id")),
    SQLAlchemy.Column("payment_id", SQLAlchemy.Integer, SQLAlchemy.ForeignKey("payments.id")),
    SQLAlchemy.Column("amount", SQLAlchemy.Float),
    SQLAlchemy.Column("status", SQLAlchemy.String(50), default="pending"),  # "pending", "approved", "rejected"
    SQLAlchemy.Column("admin_approved", SQLAlchemy.Boolean, default=False),
    SQLAlchemy.Column("created_at", SQLAlchemy.DateTime, default=SQLAlchemy.func.now()),
)

# Function to create a new user and hash the password using pwd_context
async def create_user(user):
    # Hash the password
    hashed_password = pwd_context.hash(user.hashed_password)
    # Remove 'password' from the dictionary before inserting into the DB
    user_data = user.dict(exclude={"hashed_password"})
    user_data["hashed_password"] = hashed_password
    return await database.execute(query=users.insert(), values=user_data)


# Function to get a user by username
async def get_user_by_username(username):
    query = users.select().where(users.c.username == username)
    return await database.fetch_one(query)

# Function to verify password
def verify_password(plain_password, hashed_password):
    # Use the CryptContext to verify the password
    return pwd_context.verify(plain_password, hashed_password)


# Function to store a payment record
async def store_payment(user_id: int, amount: float, status: str, payment_method: str):
    query = payments.insert().values(
        user_id=user_id,
        amount=amount,
        status=status,
        payment_method=payment_method
    )
    return await database.execute(query)


# engine is used to connect to a particular type of database like SQLite or Postgres
engine = SQLAlchemy.create_engine(
    config.DATABASE_URL,
    # connect_args={"check_same_thread": False},  # Only necessary for SQLite
)
metadata.create_all(engine)

# database variable is set to the Database object returned by using the databases module
print(config.DATABASE_URL)
print(config.DB_FORCE_ROLL_BACK)
database = databases.Database(
    url=config.DATABASE_URL, force_rollback=config.DB_FORCE_ROLL_BACK
)
