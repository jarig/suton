FROM docker.elastic.co/logstash/logstash:7.7.0

ARG TON_USER_GID=1001

# Remove example config
RUN rm -f /usr/share/logstash/pipeline/logstash.conf
RUN rm -f /usr/share/logstash/pipeline/default.conf
RUN rm -f /usr/share/logstash/config/pipelines.yml
RUN rm -f /usr/share/logstash/config/logstash-full.yml
RUN rm -f /usr/share/logstash/config/logstash-oss.yml

# Copy configs
ADD pipeline /usr/share/logstash/pipeline
ADD config /usr/share/logstash/config

USER root
RUN groupadd --gid "$TON_USER_GID" ton
RUN usermod -a -G ton logstash
RUN logstash-plugin install logstash-output-kusto
#COPY entry.sh /usr/local/bin/docker-entrypoint
#RUN chmod 0755 /usr/local/bin/docker-entrypoint

USER logstash
ENV TON_WORK_DIR=/var/ton-work
ENV TON_LOG_DIR=/var/ton-work/log
ENV TON_CONTROL_LOG_DIR=/var/ton-control/log
ENV LOGSTASH_ELASTIC_HOST=""
ENV APP_INSIGHTS_KEY=""
ENV ELASTIC_INDEX_NAME="logstash-suton-%{+YYYY.MM.dd}"

