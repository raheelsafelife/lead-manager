import fetch from 'node-fetch';

export const handler = async (event, context) => {
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ message: 'Method Not Allowed' }),
    };
  }

  try {
    const data = JSON.parse(event.body);

    // Construct payload for Google Sheets
    const sheetsPayload = {
      name: data.name,
      staff_name: data.staff_name,
      user_id: data.user_id,
      source: data.source || "SafeLife CCP Form",
      relation: data.relation,
      birthdate: data.birthdate || "",
      age: data.age || "",
      medicaid: data.medicaid,
      medicaid_number: data.medicaid_number,
      phone: data.phone,
      email: data.email,
      address_line1: data.address_line1,
      address_line2: data.address_line2,
      city: data.city,
      state: data.state,
      zip: data.zip,
      county: data.county || "",
      info: data.info
    };

    // Google Apps Script endpoint (existing integration)
    const GAS_URL = 'https://script.google.com/macros/s/AKfycbzSbjRvXSXATOWf-4IHLu8C5hkR8JpjGHuF5JgQN4eBMnsUVFttKL5OHwKW0D_FMpm5/exec';

    // Lead Manager API endpoint (new integration)
    const LEAD_MANAGER_API_URL = process.env.LEAD_MANAGER_API_URL || 'http://localhost:8000/api/external-lead';

    // Send to Google Sheets (existing flow)
    const sheetsResponse = await fetch(GAS_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sheetsPayload),
    });

    if (!sheetsResponse.ok) {
      console.error('Google Sheets error:', sheetsResponse.statusText);
      // Continue even if Google Sheets fails
    }

    // Send to Lead Manager API (new flow)
    try {
      const leadManagerResponse = await fetch(LEAD_MANAGER_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data),
      });

      if (!leadManagerResponse.ok) {
        const errorText = await leadManagerResponse.text();
        console.error('Lead Manager API error:', leadManagerResponse.statusText, errorText);
        // Log error but don't fail the submission
      } else {
        const result = await leadManagerResponse.json();
        console.log('Lead Manager success:', result);
      }
    } catch (leadManagerError) {
      console.error('Lead Manager API call failed:', leadManagerError.message);
      // Continue even if Lead Manager API fails
    }

    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
      body: JSON.stringify({ message: 'Lead submitted successfully' }),
    };
  } catch (err) {
    console.error('Error:', err.message);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: err.message }),
    };
  }
};
