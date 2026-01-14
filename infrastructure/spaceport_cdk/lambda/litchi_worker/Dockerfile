FROM public.ecr.aws/lambda/python:3.9

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright \
    PLAYWRIGHT_NODEJS_PATH=/usr/bin/node

# Install system dependencies for Playwright Chromium
RUN yum -y install \
    alsa-lib \
    atk \
    curl \
    cups-libs \
    gtk3 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    libX11-xcb \
    libXrender \
    libXfixes \
    libXinerama \
    libxcb \
    libxkbcommon \
    libdrm \
    mesa-libgbm \
    nss \
    pango \
    xorg-x11-fonts-Type1 \
    xorg-x11-fonts-misc \
  && curl -fsSL https://rpm.nodesource.com/setup_16.x | bash - \
  && yum -y install nodejs \
  && yum clean all

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN PLAYWRIGHT_NODEJS_PATH=/usr/bin/node python -m playwright install chromium

COPY lambda_function.py ./

CMD ["lambda_function.lambda_handler"]
