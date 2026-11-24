# Alondra1 landing page: static build, served by unprivileged nginx on :8080.
#   docker build -t alondra1-landing:local .
#   docker run --rm -p 127.0.0.1:8080:8080 alondra1-landing:local    # http://127.0.0.1:8080
# Links are baked in at build time (README → Configuration); changing them needs a rebuild.

FROM python:3.13-alpine AS build
WORKDIR /src
ARG SITE_URL=https://alondra1.com
ARG LOGIN_URL=
ARG REGISTER_URL=
ARG PRIVACY_URL=
ARG TERMS_URL=
ARG CONTACT_URL=
# Google Tag Manager container id (GTM-XXXXXXX). Empty = no analytics.
ARG GTM_ID=
ENV SITE_URL=${SITE_URL} LOGIN_URL=${LOGIN_URL} REGISTER_URL=${REGISTER_URL} \
    PRIVACY_URL=${PRIVACY_URL} TERMS_URL=${TERMS_URL} CONTACT_URL=${CONTACT_URL} GTM_ID=${GTM_ID}
COPY build.py ./
COPY config ./config
COPY src ./src
COPY public ./public
COPY tests ./tests
# The image is only produced when the content rules pass.
RUN python -I -m unittest discover -s tests -t . && python -I build.py --out /dist

FROM nginxinc/nginx-unprivileged:stable-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.inc /etc/nginx/conf.d/security-headers.inc
COPY --from=build /dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
