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

    const setNotificationOpen = (isOpen) => {
        notificationButton.setAttribute("aria-expanded", String(isOpen));
        notificationPanel.hidden = !isOpen;
    };

    notificationButton.addEventListener("click", (event) => {
        event.stopPropagation();
        setNotificationOpen(notificationPanel.hidden);
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".notification-wrap")) {
            setNotificationOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !notificationPanel.hidden) {
            setNotificationOpen(false);
            notificationButton.focus();
        }
    });
});
