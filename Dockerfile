FROM ubuntu:latest

LABEL maintainer="Jean-Marie Renouard <jmrenouard@gmail.com>" \
      org.opencontainers.image.title="MySQLTuner" \
      org.opencontainers.image.description="MySQLTuner is a script written in Perl that allows you to review a MySQL installation quickly and make adjustments to increase performance and stability." \
      org.opencontainers.image.version="2.6.1" \
      org.opencontainers.image.authors="Jean-Marie Renouard" \
      org.opencontainers.image.url="https://github.com/major/MySQLTuner-perl" \
      org.opencontainers.image.source="https://github.com/major/MySQLTuner-perl" \
      org.opencontainers.image.created=$(date -u +%Y-%m-%dT%H:%M:%SZ)

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt upgrade -y && apt-get install -yq --no-install-recommends \
    apt-utils \
    curl \
    wget \
    perl \
    perl-doc \
    mysql-client \
    libjson-perl \
    libtext-template-perl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /results
RUN apt clean all
WORKDIR /
COPY ./mysqltuner.pl /mysqltuner.pl 
COPY ./vulnerabilities.csv /vulnerabilities.txt
COPY ./basic_passwords.txt /basic_passwords.txt
COPY ./template_example.tpl /template.tpl

ENTRYPOINT [ "perl", "/mysqltuner.pl", "--passwordfile", "/basic_passwords.txt",\
             "--cvefile", "/vulnerabilities.txt", "--nosysstat", "--defaults-file", \
             "/defaults.cnf", "--dumpdir", "/results", "--outputfile", \
             "/results/mysqltuner.txt", "--template", "/template.tpl", \
             "--reportfile", "/results/mysqltuner.html" ]
CMD ["--verbose" ]
