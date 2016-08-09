FROM elasticsearch

COPY elasticsearch.yml /etc/elasticsearch/elasticsearch.yml
RUN chown elasticsearch /etc/elasticsearch/elasticsearch.yml
COPY elasticsearch.yml /usr/share/elasticsearch/config/elasticsearch.yml
RUN chown elasticsearch /usr/share/elasticsearch/config/elasticsearch.yml

