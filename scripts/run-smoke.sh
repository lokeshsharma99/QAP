#!/bin/bash
# Trigger smoke tests for registration page
cd automation
BASE_URL=https://demo.nopcommerce.com npx cucumber-js --tags @smoke --format progress --exit