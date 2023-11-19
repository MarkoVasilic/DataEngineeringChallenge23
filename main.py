from typing import Union, List
from pydantic import BaseModel
from fastapi import FastAPI, Depends
import datetime
from uuid import UUID
from sqlalchemy import create_engine, desc, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, Mapped
from sqlalchemy import Boolean, Column, Integer, String, Float, ForeignKey, Date, Time

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:nordeus@localhost:5432/postgres"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    #echo=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()

class Registration(Base):
    __tablename__ = "registration"

    user_id = Column(String, primary_key=True, index=True)
    date = Column(Date)
    time = Column(Time)
    name = Column(String)
    country = Column(String)
    device_os = Column(String)
    marketing_campaign = Column(String)
    sessions: Mapped[List['UserSessions']] = relationship('UserSessions', back_populates='user')
    transactions: Mapped[List['Transaction']] = relationship('Transaction', back_populates='user')

class UserSessions(Base):
    __tablename__ = "session"

    user_id = Column(String, ForeignKey(Registration.user_id))
    login_date = Column(Date)
    login_time = Column(Time)
    logout_date = Column(Date)
    logout_time = Column(Time)
    duration_seconds = Column(Integer)
    session_id = Column(Integer, primary_key=True)

    user = relationship('Registration', remote_side=[user_id], back_populates='sessions')


class Transaction(Base):
    __tablename__ = "transaction"

    user_id = Column(String, ForeignKey(Registration.user_id))
    transaction_currency = Column(String)
    transaction_amount = Column(String)
    date = Column(Date)
    time = Column(Time)
    transaction_id = Column(Integer, primary_key=True)

    user = relationship('Registration', remote_side=[user_id], back_populates='transactions')

class UserStats(BaseModel):
    country: str | None = None
    name: str | None = None
    number_of_logins: int | None = None
    days_since_last_login: int | None = None
    number_of_sessions: int | None = None
    time_spent_seconds: int | None = None

class GameStats(BaseModel):
    daily_active_users: int | None = None
    number_of_logins: int | None = None
    total_revenue: float | None = None
    number_paid_users: int | None = None
    avg_num_of_sessions: float | None = None
    avg_total_time_spent: float | None = None

app = FastAPI()

@app.get("/api/users/{user_id}/stats")
def get_user_stats(user_id: UUID, date: Union[datetime.date, None] = None, db: Session = Depends(get_db)):
    user = db.query(Registration).filter(Registration.user_id == str(user_id)).first()
    if user == None:
        return "Not Found", 404
    login_number = db.query(UserSessions).filter(UserSessions.user_id == str(user_id)).count()
    last_login = db.query(UserSessions).filter(UserSessions.user_id == str(user_id)).order_by(desc(UserSessions.login_date)).first().login_date
    if(date == None):
        last_date = db.query(UserSessions).filter(UserSessions.logout_date.isnot(None)).order_by(desc(UserSessions.logout_date)).first().logout_date
        num_of_days = last_date - last_login
        num_of_sessions = login_number
        time_spent = db.query(func.sum(UserSessions.duration_seconds)).filter(UserSessions.user_id == str(user_id)).scalar()
    else:
        num_of_days = date - last_login
        num_of_sessions = db.query(UserSessions).filter(UserSessions.user_id == str(user_id), UserSessions.login_date == date).count()
        time_spent = db.query(func.sum(UserSessions.duration_seconds)).filter(UserSessions.user_id == str(user_id), UserSessions.login_date == date).scalar()
    return UserStats(country=user.country, name=user.name, number_of_logins=login_number, days_since_last_login=abs(num_of_days.days), number_of_sessions=num_of_sessions, time_spent_seconds=time_spent)

@app.get("/api/game/stats")
def get_game_stats(date: Union[datetime.date, None] = None, country: str = None, db: Session = Depends(get_db)):
    if date == None and country == None:
        daily_users = db.query(func.count(func.distinct(UserSessions.user_id))).scalar()
        num_of_logins = db.query(UserSessions).count()
        total_revenue = db.query(func.sum(Transaction.transaction_amount)).scalar()
        paid_users = db.query(func.count(func.distinct(Transaction.user_id))).scalar()
        session_counts_per_user = (
            db.query(UserSessions.user_id, func.count(UserSessions.user_id).label('session_count'))
            .group_by(UserSessions.user_id)
            .all()
        )
        total_sessions = sum(count for user_id, count in session_counts_per_user)
        avg_sessions = total_sessions / len(session_counts_per_user) if session_counts_per_user else 0
        average_time_spent = (
            db.query(func.avg(UserSessions.duration_seconds))
            .filter(UserSessions.duration_seconds > 0)
            .scalar()
        )
    elif date == None and country != None:
        daily_users = db.query(func.count(func.distinct(UserSessions.user_id))).join(Registration, UserSessions.user_id == Registration.user_id).filter(Registration.country == country).scalar()
        num_of_logins = db.query(UserSessions).join(Registration, UserSessions.user_id == Registration.user_id).filter(Registration.country == country).count()
        total_revenue = db.query(func.sum(Transaction.transaction_amount)).join(Registration, Transaction.user_id == Registration.user_id).filter(Registration.country == country).scalar()
        paid_users = db.query(func.count(func.distinct(Transaction.user_id))).join(Registration, Transaction.user_id == Registration.user_id).filter(Registration.country == country).scalar()
        session_counts_per_user = (
            db.query(UserSessions.user_id, func.count(UserSessions.user_id).label('session_count'))
            .join(Registration, UserSessions.user_id == Registration.user_id).filter(Registration.country == country)
            .group_by(UserSessions.user_id)
            .all()
        )
        total_sessions = sum(count for user_id, count in session_counts_per_user)
        avg_sessions = total_sessions / len(session_counts_per_user) if session_counts_per_user else 0
        average_time_spent = (
            db.query(func.avg(UserSessions.duration_seconds))
            .join(Registration, UserSessions.user_id == Registration.user_id).filter(Registration.country == country)
            .filter(UserSessions.duration_seconds > 0)
            .scalar()
        )
    elif date != None and country == None:
        daily_users = db.query(func.count(func.distinct(UserSessions.user_id))).filter(UserSessions.login_date == date).scalar()
        num_of_logins = db.query(UserSessions).filter(UserSessions.login_date == date).count()
        total_revenue = db.query(func.sum(Transaction.transaction_amount)).filter(Transaction.date == date).scalar()
        paid_users = db.query(func.count(func.distinct(Transaction.user_id))).filter(Transaction.date == date).scalar()
        session_counts_per_user = (
            db.query(UserSessions.user_id, func.count(UserSessions.user_id).label('session_count'))
            .filter(UserSessions.login_date == date)
            .group_by(UserSessions.user_id)
            .all()
        )
        total_sessions = sum(count for user_id, count in session_counts_per_user)
        avg_sessions = total_sessions / len(session_counts_per_user) if session_counts_per_user else 0
        average_time_spent = (
            db.query(func.avg(UserSessions.duration_seconds))
            .filter(UserSessions.login_date == date)
            .filter(UserSessions.duration_seconds > 0)
            .scalar()
        )
    else:
        daily_users = db.query(func.count(func.distinct(UserSessions.user_id))).join(Registration, UserSessions.user_id == Registration.user_id).filter(Registration.country == country).filter(UserSessions.login_date == date).scalar()
        num_of_logins = db.query(UserSessions).join(Registration, UserSessions.user_id == Registration.user_id).filter(Registration.country == country, UserSessions.login_date == date).count()
        total_revenue = db.query(func.sum(Transaction.transaction_amount)).join(Registration, Transaction.user_id == Registration.user_id).filter(Registration.country == country, Transaction.date == date).scalar()
        paid_users = db.query(func.count(func.distinct(Transaction.user_id))).join(Registration, Transaction.user_id == Registration.user_id).filter(Registration.country == country, Transaction.date == date).scalar()
        session_counts_per_user = (
            db.query(UserSessions.user_id, func.count(UserSessions.user_id).label('session_count'))
            .join(Registration, UserSessions.user_id == Registration.user_id).filter(Registration.country == country, UserSessions.login_date == date)
            .group_by(UserSessions.user_id)
            .all()
        )
        total_sessions = sum(count for user_id, count in session_counts_per_user)
        avg_sessions = total_sessions / len(session_counts_per_user) if session_counts_per_user else 0
        average_time_spent = (
            db.query(func.avg(UserSessions.duration_seconds))
            .join(Registration, UserSessions.user_id == Registration.user_id).filter(Registration.country == country, UserSessions.login_date == date)
            .filter(UserSessions.duration_seconds > 0)
            .scalar()
        )
    print(average_time_spent)
    return GameStats(daily_active_users=daily_users, number_of_logins=num_of_logins, total_revenue=total_revenue, number_paid_users=paid_users, avg_num_of_sessions=avg_sessions, avg_total_time_spent=average_time_spent)