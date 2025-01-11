# models.py

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class UserReputation(Base):
    __tablename__ = 'user_reputations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    reputation = Column(Float, default=0.0)
    last_modified = Column(DateTime, server_default=func.now())

class ReputationChange(Base):
    __tablename__ = 'reputation_changes'

    id = Column(Integer, primary_key=True)
    source_user_id = Column(Integer, ForeignKey('user_reputations.user_id'), nullable=False)
    target_user_id = Column(Integer, ForeignKey('user_reputations.user_id'), nullable=False)
    change = Column(Float, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    source_user = relationship("UserReputation", foreign_keys=[source_user_id])
    target_user = relationship("UserReputation", foreign_keys=[target_user_id])