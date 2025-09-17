document.addEventListener("DOMContentLoaded", () => {
    const expiryElement = document.getElementById("expiry");
    const expiryAt = expiryElement.dataset.expiry;
    if (typeof expiryAt !== "undefined") {
        const localTime = new Date(expiryAt).toLocaleString(); // Convert to local time
        document.getElementById("expiry-at").textContent = localTime; // Display in the placeholder
    }
});

window.onload = function() {
    const invitationUrlElement = document.getElementById("invitation-url");
    const invitationUrl = invitationUrlElement.dataset.url;
        // Generate QR code
        var qr = qrcode(0, 'M');
        qr.addData(invitationUrl);
        qr.make();

        document.getElementById('qrcode').innerHTML = qr.createImgTag(5);
    };