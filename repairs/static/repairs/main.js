// repairs/static/repairs/js/main.js
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('reqForm');
  const otpSection = document.getElementById('otp-section');
  let tempId = null;

  if (!form) return;

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const data = new FormData(form);
    try {
      const res = await fetch('/request-otp/', { method: 'POST', body: data });
      const json = await res.json();
      if (json.success) {
        tempId = json.temp_id;
        localStorage.setItem('repair_temp_id', tempId);
        otpSection.style.display = 'block';
        alert('OTP sent (check server console for mock SMS).');
      } else {
        alert('Error: ' + (json.error || 'unknown'));
      }
    } catch (err) {
      alert('Network error');
    }
  });

  const verifyBtn = document.getElementById('verifyBtn');
  if (verifyBtn) {
    verifyBtn.addEventListener('click', async function () {
      const otp = document.getElementById('otp').value;
      const formData = new FormData();
      formData.append('temp_id', localStorage.getItem('repair_temp_id'));
      formData.append('otp', otp);
      try {
        const res = await fetch('/verify-otp/', { method: 'POST', body: formData });
        const json = await res.json();
        if (json.success) {
          alert('Job created: ' + json.job_id);
          window.location = `/jobs/${json.job_id}/`;
        } else {
          alert('Verify error: ' + (json.error || 'unknown'));
        }
      } catch (err) {
        alert('Network error');
      }
    });
  }
});
