const authSwitch = document.querySelector(".auth-switch");
const authTabs = Array.from(document.querySelectorAll("[data-auth-mode]"));
const authForms = Array.from(document.querySelectorAll("[data-auth-form]"));
const authFeedback = document.getElementById("auth-feedback");

function showFeedback(message, success = false) {
    authFeedback.textContent = message;
    authFeedback.classList.toggle("is-success", success);
    authFeedback.hidden = false;
}

function clearFeedback() {
    authFeedback.textContent = "";
    authFeedback.classList.remove("is-success");
    authFeedback.hidden = true;
}

function setAuthMode(mode, focusTab = false) {
    const isRegister = mode === "register";
    authSwitch.classList.toggle("is-register", isRegister);

    authTabs.forEach((tab) => {
        const isActive = tab.dataset.authMode === mode;
        tab.classList.toggle("is-active", isActive);
        tab.setAttribute("aria-selected", String(isActive));
        tab.tabIndex = isActive ? 0 : -1;
        if (isActive && focusTab) tab.focus();
    });

    authForms.forEach((form) => {
        form.hidden = form.dataset.authForm !== mode;
    });

    document.getElementById("auth-heading").textContent = isRegister ? "Make it yours." : "Come on in.";
    document.title = isRegister ? "Create Account | Dickens Cafe" : "Sign In | Dickens Cafe";
    clearFeedback();
}

authTabs.forEach((tab, index) => {
    tab.addEventListener("click", () => setAuthMode(tab.dataset.authMode));
    tab.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const nextIndex = (index + (event.key === "ArrowRight" ? 1 : -1) + authTabs.length) % authTabs.length;
        setAuthMode(authTabs[nextIndex].dataset.authMode, true);
    });
});

document.querySelectorAll("[data-password-target]").forEach((button) => {
    button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.passwordTarget);
        const showPassword = input.type === "password";
        input.type = showPassword ? "text" : "password";
        button.textContent = showPassword ? "Hide" : "Show";
        button.setAttribute("aria-label", `${showPassword ? "Hide" : "Show"} password`);
    });
});

document.querySelectorAll("[data-local-link]").forEach((link) => {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        showFeedback("Password recovery and policy details are not available yet.");
    });
});

const registerPassword = document.getElementById("register-password");
const registerConfirmation = document.getElementById("register-confirm");
const validatePasswordMatch = () => {
    const mismatch = registerConfirmation.value && registerPassword.value !== registerConfirmation.value;
    registerConfirmation.setCustomValidity(mismatch ? "Passwords do not match." : "");
};

registerPassword.addEventListener("input", validatePasswordMatch);
registerConfirmation.addEventListener("input", validatePasswordMatch);

authForms.forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        clearFeedback();

        if (!form.reportValidity()) return;

        const submitButton = form.querySelector('[type="submit"]');
        submitButton.disabled = true;

        try {
            const endpoint = form.dataset.authForm === "register" ? "/register" : "/login";
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(Object.fromEntries(new FormData(form)))
            });
            const result = await response.json();

            if (!response.ok) {
                showFeedback(result.error || "Unable to complete your request.");
                return;
            }

            showFeedback(result.message, true);
            window.location.assign("/");
        } catch {
            showFeedback("We could not reach the server. Please try again.");
        } finally {
            submitButton.disabled = false;
        }
    });
});