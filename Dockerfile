FROM python:3.5.2-slim
MAINTAINER John Thomas <netflixemailaccount@gmail.com>

RUN apt-get update && apt-get install -qq -y \
  build-essential libpq-dev libxml2-dev libxslt-dev \
  libjpeg-dev zlib1g-dev libpng12-dev \
  --no-install-recommends

ENV INSTALL_PATH /watt_app
RUN mkdir -p $INSTALL_PATH

WORKDIR $INSTALL_PATH

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
#The following line is needed for Click
#RUN pip install --editable .

CMD gunicorn -b 0.0.0.0:8989 --access-logfile - "watt_app.app:create_app()"
