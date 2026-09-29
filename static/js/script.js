function togglePassword() {

    const passwordInput =
        document.getElementById("password");

    const toggleButton =
        document.querySelector(".password-toggle");


    const isPasswordHidden = passwordInput.type === "password";
    passwordInput.type = isPasswordHidden ? "text" : "password";

    toggleButton.querySelector(".password-eye").hidden = isPasswordHidden;
    toggleButton.querySelector(".password-eye-crossed").hidden = !isPasswordHidden;
    toggleButton.setAttribute(
        "aria-label",
        isPasswordHidden ? "Hide password" : "Show password"
    );
}

document.addEventListener("DOMContentLoaded", () => {
    const notificationButton = document.querySelector(".navbar-notification");
    const notificationPanel = document.getElementById("notification-panel");

    if (!notificationButton || !notificationPanel) return;

    notificationButton.addEventListener("click", () => {
        const isOpen = notificationButton.getAttribute("aria-expanded") === "true";
        notificationButton.setAttribute("aria-expanded", String(!isOpen));
        notificationPanel.hidden = isOpen;
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".notification-wrap")) {
            notificationButton.setAttribute("aria-expanded", "false");
            notificationPanel.hidden = true;
        }
    });
});
