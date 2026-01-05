const API_BASE = "http://127.0.0.1:8000";

// --------------------
// SEARCH FLIGHTS
// --------------------
async function searchFlights() {
    const origin = document.getElementById("origin").value.trim();
    const destination = document.getElementById("destination").value.trim();
    const date = document.getElementById("date").value;

    let url = `${API_BASE}/flights?origin=${origin}&destination=${destination}`;
    if (date) url += `&date=${date}`;

    const response = await fetch(url);
    const flights = await response.json();

    const tbody = document.querySelector("#flightsTable tbody");
    tbody.innerHTML = "";

    if (flights.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7">No flights found</td></tr>`;
        return;
    }

    flights.forEach(flight => {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${flight.id}</td>
            <td>${flight.flight_number}</td>
            <td>${flight.origin_airport_id}</td>
            <td>${flight.destination_airport_id}</td>
            <td>${new Date(flight.departure).toLocaleString()}</td>
            <td>₹ ${flight.dynamic_price.toFixed(2)}</td>
            <td>
                <button onclick="selectFlight(${flight.id})">Select</button>
            </td>
        `;

        tbody.appendChild(row);
    });
}

// --------------------
// SELECT FLIGHT
// --------------------
function selectFlight(flightId) {
    document.getElementById("flightId").value = flightId;
}

// --------------------
// CREATE BOOKING
// --------------------
async function createBooking() {
    const flightId = document.getElementById("flightId").value;
    const name = document.getElementById("passengerName").value;
    const age = document.getElementById("passengerAge").value;

    if (!flightId || !name || !age) {
        document.getElementById("bookingResult").innerText =
            "❌ Please fill all fields";
        return;
    }

    const payload = {
        flight_id: parseInt(flightId),
        seats: 1,
        passengers: [{ name, age: parseInt(age) }]
    };

    const response = await fetch(`${API_BASE}/bookings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (response.ok) {
        document.getElementById("bookingResult").innerText =
            `✅ Booking Confirmed! PNR: ${result.pnr}`;
        document.getElementById("cancelPnr").value = result.pnr;
    } else {
        document.getElementById("bookingResult").innerText =
            `❌ ${result.detail}`;
    }
}

// --------------------
// CANCEL BOOKING
// --------------------
async function cancelBooking() {
    const pnr = document.getElementById("cancelPnr").value;

    const response = await fetch(`${API_BASE}/bookings/${pnr}/cancel`, {
        method: "POST"
    });

    const result = await response.json();

    if (response.ok) {
        document.getElementById("cancelResult").innerText =
            `✅ Booking cancelled: ${pnr}`;
    } else {
        document.getElementById("cancelResult").innerText =
            `❌ ${result.detail}`;
    }
}
// --------------------
// BOOKING HISTORY
// --------------------
async function loadBookingHistory() {
    const response = await fetch(`${API_BASE}/bookings/history`);
    const bookings = await response.json();

    const tbody = document.querySelector("#historyTable tbody");
    tbody.innerHTML = "";

    bookings.forEach(b => {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${b.pnr}</td>
            <td>${b.flight_id}</td>
            <td>${b.seats}</td>
            <td>₹ ${b.total_price.toFixed(2)}</td>
            <td>${b.status}</td>
            <td>${new Date(b.created_at).toLocaleString()}</td>
        `;

        tbody.appendChild(row);
    });
}
// --------------------
// DOWNLOAD RECEIPT
// --------------------
async function downloadReceipt() {
    const pnr = document.getElementById("receiptPnr").value;

    if (!pnr) {
        alert("Please enter PNR");
        return;
    }

    const response = await fetch(`${API_BASE}/bookings/${pnr}/receipt`);

    if (!response.ok) {
        document.getElementById("receiptStatus").innerText =
            "Receipt not found!";
        return;
    }

    const receipt = await response.json();

    const blob = new Blob(
        [JSON.stringify(receipt, null, 2)],
        { type: "application/json" }
    );

    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `receipt_${pnr}.json`;
    link.click();

    document.getElementById("receiptStatus").innerText =
        "Receipt downloaded successfully!";
}
// --------------------
// DOWNLOAD PDF RECEIPT
// --------------------
function downloadPdfReceipt() {
    const pnr = document.getElementById("pdfPnr").value;

    if (!pnr) {
        alert("Please enter PNR");
        return;
    }

    window.open(`${API_BASE}/bookings/${pnr}/receipt/pdf`, "_blank");

    document.getElementById("pdfStatus").innerText =
        "PDF receipt downloaded!";
}