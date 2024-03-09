FROM docker.elastic.co/logstash/logstash:7.7.1

ARG TON_USER_GID=1001

# Remove example config
RUN rm -f /usr/share/logstash/pipeline/logstash.conf
RUN rm -f /usr/share/logstash/pipeline/default.conf
RUN rm -f /usr/share/logstash/config/pipelines.yml
RUN rm -f /usr/share/logstash/config/logstash-full.yml
RUN rm -f /usr/share/logstash/config/logstash-oss.yml

USER root
RUN groupadd --gid "$TON_USER_GID" ton
RUN usermod -a -G ton logstash
RUN logstash-plugin install logstash-output-kusto
RUN logstash-plugin install logstash-output-datadog_metrics
RUN logstash-plugin install logstash-output-exec
COPY entry.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entry.sh

RUN yum update -y && yum install -y sudo
#RUN apt-get update && \
#    apt-get install --no-install-recommends -y sudo
RUN echo "logstash ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers


USER logstash

# Copy configs
ADD pipeline /usr/share/logstash/pipeline
ADD config /usr/share/logstash/config


ENV TON_WORK_DIR=/var/ton-work
ENV TON_CONTROL_WORK_DIR=/var/ton-control
ENV TON_LOG_DIR=$TON_WORK_DIR/log
ENV TON_CONTROL_LOG_DIR=$TON_CONTROL_WORK_DIR/log
ENV LOGSTASH_HOST_DATA_INPUT_PORT=$LOGSTASH_HOST_DATA_INPUT_PORT

ENTRYPOINT ["/usr/local/bin/entry.sh"]
