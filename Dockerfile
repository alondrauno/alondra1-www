# Alondra1 landing page: static build of both variants (dev, prod), served by unprivileged nginx on :8080.
#   docker build -t alondra1-landing:local .
#   docker run --rm -e ALONDRA1_ENVIRONMENT=dev -p 127.0.0.1:8080:8080 alondra1-landing:local   # http://127.0.0.1:8080
# One image for every environment: prod runs the exact digest that passed in dev; ALONDRA1_ENVIRONMENT picks the variant.

FROM python:3.13-alpine@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e AS build
WORKDIR /src
COPY build.py ./
COPY config ./config
COPY src ./src
COPY public ./public
COPY tests ./tests
COPY nginx ./nginx
# The image is only produced when the content rules pass.
RUN python -I -m unittest discover -s tests -t . && python -I build.py --out /dist

FROM nginxinc/nginx-unprivileged:stable-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03
# Security updates (the release scan fails on fixable high or critical issues, and the base tag is not always rebuilt
# in time): Alpine packages from Alpine, nginx from nginx.org's stable repository, whose signing key is checked against
# a pinned SHA-512 (as the official nginx images do). The image still runs as the unprivileged nginx user.
ARG NGINX_KEY_SHA512=e09fa32f0a0eab2b879ccbbc4d0e4fb9751486eedda75e35fac65802cc9faa266425edf83e261137a2f4d16281ce2c1a5f4502930fe75154723da014214f0655
USER root
# The base pins nginx and its modules to exact versions: adding them by name drops the pin and takes the newest from
# nginx.org. The build fails if nginx is still the vulnerable 1.30.6.
RUN set -eux; \
    wget -q -O /tmp/nginx_signing.rsa.pub https://nginx.org/keys/nginx_signing.rsa.pub; \
    echo "${NGINX_KEY_SHA512}  /tmp/nginx_signing.rsa.pub" | sha512sum -c -; \
    mv /tmp/nginx_signing.rsa.pub /etc/apk/keys/; \
    apk upgrade --no-cache; \
    apk add --no-cache --upgrade -X "https://nginx.org/packages/alpine/v$(cut -d. -f1,2 /etc/alpine-release)/main" $(apk info | grep '^nginx'); \
    nginx -v 2>&1 | tee /tmp/nginx-version; \
    if grep -q 'nginx/1\.30\.6$' /tmp/nginx-version; then echo 'nginx was not upgraded' >&2; exit 1; fi; \
    rm /tmp/nginx-version
USER 101
# Templates are rendered into conf.d at start (envsubst replaces only ALONDRA1_ENVIRONMENT; nginx variables stay).
ENV NGINX_ENVSUBST_FILTER=^ALONDRA1_
COPY nginx/templates/ /etc/nginx/templates/
COPY nginx/snippets/ /etc/nginx/snippets/
COPY --chmod=0755 nginx/05-alondra1-environment.sh /docker-entrypoint.d/05-alondra1-environment.sh
COPY --from=build /dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3   CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
