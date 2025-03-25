from sqlalchemy import Column, BigInteger, Text, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class LiveRoom(Base):
    """B站直播间数据模型"""
    __tablename__ = "bilibili_live_rooms"

    room_id = Column(BigInteger, primary_key=True, index=True)
    uid = Column(BigInteger, nullable=True)
    title = Column(Text, nullable=True)
    uname = Column(Text, nullable=True)
    online = Column(Integer, nullable=True)
    user_cover = Column(Text, nullable=True)
    system_cover = Column(Text, nullable=True)
    cover = Column(Text, nullable=True)
    link = Column(Text, nullable=True)
    face = Column(Text, nullable=True)
    parent_id = Column(Integer, nullable=True)
    parent_name = Column(Text, nullable=True)
    area_id = Column(Integer, nullable=True)
    area_name = Column(Text, nullable=True)
    area_v2_id = Column(Integer, nullable=True)
    area_v2_name = Column(Text, nullable=True)
    session_id = Column(Text, nullable=True)
    group_id = Column(Integer, nullable=True)
    show_callback = Column(Text, nullable=True)
    click_callback = Column(Text, nullable=True)
    watched_num = Column(Integer, nullable=True)
    watched_text = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __str__(self):
        return f"{self.uname}的直播间: {self.title}"

