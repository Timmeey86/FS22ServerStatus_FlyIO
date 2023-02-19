FROM python:3.10
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip install -r requirements.txt
COPY ./src /bot/
CMD python main.py