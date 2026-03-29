const registrationForm = document.getElementById("registration-form");
const regError = document.createElement("div");
regError.className = "error";

function showRegError(msg) {
  regError.textContent = msg;
  if (!registrationForm.contains(regError)) {
    registrationForm.appendChild(regError);
  }
}

function wirePasswordToggles(formRoot) {
  const toggles = formRoot.querySelectorAll(".toggle-password");
  toggles.forEach((btn) => {
    const targetId = btn.getAttribute("data-target");
    if (!targetId) return;
    const input = formRoot.querySelector(`#${targetId}`);
    if (!input) return;

    btn.addEventListener("click", () => {
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      btn.textContent = isHidden ? "Hide" : "Show";
    });
  });
}

if (registrationForm) {
  wirePasswordToggles(registrationForm);

  registrationForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    regError.remove?.();

    const email = registrationForm.email.value.trim();
    const password = registrationForm.password.value.trim();
    const confirm = registrationForm["confirm-password"].value.trim();

    if (!email || !password || !confirm) {
      showRegError("All fields are required.");
      return;
    }

    if (password !== confirm) {
      showRegError("Passwords do not match.");
      return;
    }

    if (password.length < 8 || password.length > 20) {
      showRegError("Password must be 8-20 characters.");
      return;
    }

    const formData = new FormData();
    formData.append("email", email);
    formData.append("password", password);

    try {
      const res = await fetch("/registration", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Registration failed");
      }
      window.location.href = "/login";
    } catch (err) {
      showRegError(err.message || "Registration failed");
    }
  });
}
