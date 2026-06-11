class CruiseChatClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.sessionId = crypto.randomUUID();
    }

    /**
     * Sends a message to the AI and yields streamed responses.
     */
    async *sendMessage(message) {
        const response = await fetch(`${this.baseUrl}/api/cruise-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': this.apiKey
            },
            body: JSON.stringify({
                session_id: this.sessionId,
                message: message
            })
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            
            // Process SSE data frames
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // Keep incomplete chunk in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    if (dataStr === '[DONE]') {
                        return; // Stream finished
                    }
                    try {
                        const data = JSON.parse(dataStr);
                        yield data;
                    } catch (e) {
                        console.error('Error parsing SSE data:', e, dataStr);
                    }
                }
            }
        }
    }

    /**
     * Polls the booking status endpoint.
     */
    async checkBookingStatus(bookingId) {
        const response = await fetch(`${this.baseUrl}/api/booking-status/${bookingId}`, {
            method: 'GET',
            headers: {
                'X-API-Key': this.apiKey
            }
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    }

    /**
     * Securely executes the final booking.
     */
    async executeBooking(bookingId, paymentToken) {
        const response = await fetch(`${this.baseUrl}/api/execute-booking`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': this.apiKey
            },
            body: JSON.stringify({
                session_id: this.sessionId,
                booking_id: bookingId,
                payment_token: paymentToken
            })
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    }
}
