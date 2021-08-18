FROM ubuntu:16.04
RUN apt-get update
RUN apt-get install -y python3 python3-pip
RUN pip3 install flask pymongo
RUN mkdir /DSmarkets
RUN mkdir -p /DSmarkets/data
COPY app.py /DSmarkets/app.py
ADD data /DSmarkets/data
EXPOSE 5000 
WORKDIR /DSmarkets
ENTRYPOINT [ "python3","-u", "app.py" ]
