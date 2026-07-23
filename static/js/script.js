document.addEventListener("DOMContentLoaded", function () {
    console.log("Welcome to CareOrbit!");

    const navLinks = document.querySelectorAll(".nav-link");

    navLinks.forEach(link => {
        link.addEventListener("click", function () {
            navLinks.forEach(item => item.classList.remove("active"));
            this.classList.add("active");
        });
    });
});
//password show /Hide Function
function togglePassword(id, icon) {

    const passwordField = document.getElementById(id);
    const eyeIcon = icon.querySelector("i");

    if (passwordField.type === "password") {

        passwordField.type = "text";
        eyeIcon.classList.replace("fa-eye", "fa-eye-slash");

    } else {

        passwordField.type = "password";
        eyeIcon.classList.replace("fa-eye-slash", "fa-eye");

    }
}