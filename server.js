const cds = require('@sap/cds');
const path = require('path');
const express = require('express');

cds.on('bootstrap', (app) => {
  // Serve the app folder as static content at /app
  app.use('/app', express.static(path.join(__dirname, 'app')));
});

module.exports = cds.server;
