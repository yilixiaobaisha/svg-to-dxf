#randyp/svg-to-dxf
# vim:set ft=dockerfile:

FROM python:2.7.10

RUN easy_install ezdxf==0.6.5
RUN easy_install web.py==0.37
RUN easy_install svg.path==2.0
RUN easy_install pysvg==0.2.2

ADD src/*.py /root/

EXPOSE 8080
CMD ["python", "/root/server.py"]

