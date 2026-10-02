/**
 * SAP AI Core Proxy Server
 * Handles OAuth authentication and forwards prediction requests
 * 
 * Lab 5: Web UI for Churn Predictions
 */

const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();
const PORT = 3000;

// ===========================================
// SAP AI Core Configuration
// ===========================================
const CONFIG = {
    // OAuth credentials (from your SAP BTP service key)
    CLIENT_ID: 'sb-a734d6cf-0507-4b7e-9dbd-8c4c7a00c716!b612484|aicore!b164',
    CLIENT_SECRET: '06a1a7d1-4204-48fd-91ac-beeaed25794b$k5Xli8of30DtE1_PeKau5FOG72SjcIJaofEcKPnw-Ss=',
    
    // URLs
    AUTH_URL: 'https://sap-btp-joule.authentication.us10.hana.ondemand.com',
    AI_API_URL: 'https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com',
    
    // Deployment
    DEPLOYMENT_ID: 'd74ee8a32f950025',
    RESOURCE_GROUP: 'default'
};

// Token cache
let cachedToken = null;
let tokenExpiry = null;

// ===========================================
// Middleware
// ===========================================
app.use(cors());
app.use(express.json());
app.use(express.static('.')); // Serve static files (index.html)

// ===========================================
// Get OAuth Token
// ===========================================
async function getAccessToken() {
    // Check if cached token is still valid (with 5 min buffer)
    if (cachedToken && tokenExpiry && Date.now() < tokenExpiry - 300000) {
        console.log('Using cached token');
        return cachedToken;
    }

    console.log('Fetching new OAuth token...');
    
    const tokenUrl = `${CONFIG.AUTH_URL}/oauth/token`;
    const params = new URLSearchParams({
        grant_type: 'client_credentials',
        client_id: CONFIG.CLIENT_ID,
        client_secret: CONFIG.CLIENT_SECRET
    });

    try {
        const response = await fetch(tokenUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: params
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Token request failed: ${response.status} - ${error}`);
        }

        const data = await response.json();
        cachedToken = data.access_token;
        tokenExpiry = Date.now() + (data.expires_in * 1000);
        
        console.log('Token obtained successfully');
        return cachedToken;

    } catch (error) {
        console.error('Error getting token:', error);
        throw error;
    }
}

// ===========================================
// Prediction Endpoint
// ===========================================
app.post('/predict', async (req, res) => {
    console.log('\n--- Prediction Request ---');
    console.log('Input:', JSON.stringify(req.body, null, 2));

    try {
        // Get OAuth token
        const token = await getAccessToken();

        // Build prediction URL
        const predictionUrl = `${CONFIG.AI_API_URL}/v2/inference/deployments/${CONFIG.DEPLOYMENT_ID}/v2/predict`;
        console.log('Calling:', predictionUrl);

        // Make prediction request
        const response = await fetch(predictionUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'AI-Resource-Group': CONFIG.RESOURCE_GROUP,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(req.body)
        });

        if (!response.ok) {
            const error = await response.text();
            console.error('Prediction API error:', error);
            return res.status(response.status).json({ 
                error: 'Prediction failed', 
                details: error 
            });
        }

        const result = await response.json();
        console.log('Result:', JSON.stringify(result, null, 2));
        
        res.json(result);

    } catch (error) {
        console.error('Server error:', error);
        res.status(500).json({ 
            error: 'Server error', 
            message: error.message 
        });
    }
});

// ===========================================
// Health Check Endpoint
// ===========================================
app.get('/health', async (req, res) => {
    try {
        const token = await getAccessToken();
        
        const healthUrl = `${CONFIG.AI_API_URL}/v2/inference/deployments/${CONFIG.DEPLOYMENT_ID}/v2/health`;
        
        const response = await fetch(healthUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'AI-Resource-Group': CONFIG.RESOURCE_GROUP
            }
        });

        const data = await response.json();
        res.json({
            proxy: 'healthy',
            model: data
        });

    } catch (error) {
        res.status(500).json({ 
            proxy: 'healthy',
            model: 'unreachable',
            error: error.message 
        });
    }
});

// ===========================================
// Info Endpoint
// ===========================================
app.get('/info', (req, res) => {
    res.json({
        name: 'SAP AI Core Proxy Server',
        version: '1.0.0',
        deployment_id: CONFIG.DEPLOYMENT_ID,
        ai_core_url: CONFIG.AI_API_URL,
        endpoints: {
            predict: 'POST /predict',
            health: 'GET /health',
            info: 'GET /info'
        }
    });
});

// ===========================================
// Start Server
// ===========================================
app.listen(PORT, () => {
    console.log('╔════════════════════════════════════════════════╗');
    console.log('║   SAP AI Core Proxy Server                     ║');
    console.log('║   Lab 5: Web UI for Churn Predictions          ║');
    console.log('╠════════════════════════════════════════════════╣');
    console.log(`║   Server running on: http://localhost:${PORT}      ║`);
    console.log(`║   Deployment ID: ${CONFIG.DEPLOYMENT_ID}  ║`);
    console.log('╠════════════════════════════════════════════════╣');
    console.log('║   Endpoints:                                   ║');
    console.log('║   - GET  /         → Web UI                    ║');
    console.log('║   - POST /predict  → Make prediction           ║');
    console.log('║   - GET  /health   → Check model health        ║');
    console.log('║   - GET  /info     → Server info               ║');
    console.log('╚════════════════════════════════════════════════╝');
});
