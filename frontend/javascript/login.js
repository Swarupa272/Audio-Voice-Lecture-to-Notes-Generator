const loginForm = document.getElementById("login-form");
const errorBox = document.createElement("div");
errorBox.className = "error";

const forgotToggle = document.getElementById("forgot-toggle");
const forgotPanel = document.getElementById("forgot-panel");
const forgotForm = document.getElementById("forgot-form");
const resetForm = document.getElementById("reset-form");
const forgotResult = document.getElementById("forgot-result");
const resetResult = document.getElementById("reset-result");

function showError(msg) {
  errorBox.textContent = msg;
  if (!loginForm.contains(errorBox)) {
    loginForm.appendChild(errorBox);
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

function setInfo(el, msg, isError = false) {
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
}

if (loginForm) {
  wirePasswordToggles(loginForm);

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.remove?.();

    const email = loginForm.email.value.trim();
    const password = loginForm.password.value.trim();

    if (!email || !password) {
      showError("Email and password are required.");
      return;
    }

    const formData = new FormData();
    formData.append("email", email);
    formData.append("password", password);

    try {
      const res = await fetch("/login", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }

      window.location.href = data.redirect || "/index.html";
    } catch (err) {
      showError(err.message || "Login failed");
    }
  });
}

const forgotLinks = document.querySelectorAll(".forgot-password");
if (forgotLinks.length) {
  forgotLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      alert("To reset your password, please contact support or check your email for reset instructions.");
    });
  });
}

if (forgotToggle && forgotPanel) {
  forgotToggle.addEventListener("click", () => {
    forgotPanel.classList.toggle("hidden");
  });
}

if (forgotForm) {
  forgotForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setInfo(forgotResult, "");
    const email = forgotForm.email.value.trim();
    if (!email) return setInfo(forgotResult, "Email is required", true);

    const formData = new FormData();
    formData.append("email", email);

    try {
      const res = await fetch("/password/forgot", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to start reset");
      const tokenNote = data.token ? ` Token: ${data.token}` : "";
      setInfo(
        forgotResult,
        `${data.message || "Check your email for reset instructions."}${tokenNote}`
      );
    } catch (err) {
      setInfo(forgotResult, err.message || "Failed to start reset", true);
    }
  });
}

if (resetForm) {
  resetForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    setInfo(resetResult, "");

    const token = resetForm.token.value.trim();
    const newPassword = resetForm.new_password.value.trim();

    if (!token) return setInfo(resetResult, "Token is required", true);
    if (!newPassword) return setInfo(resetResult, "New password is required", true);

    const formData = new FormData();
    formData.append("token", token);
    formData.append("new_password", newPassword);

    try {
      const res = await fetch("/password/reset", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Reset failed");
      setInfo(resetResult, data.message || "Password reset. Please log in.");
    } catch (err) {
      setInfo(resetResult, err.message || "Reset failed", true);
    }
  });
}
