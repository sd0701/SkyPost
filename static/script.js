document.addEventListener("DOMContentLoaded", function () {
    const accountSelector = document.getElementById("accountSelector");
    const folderList = document.getElementById("folderList");
    const searchBar = document.getElementById("searchBar");
    const searchButton = document.getElementById("searchButton");
    const emailList = document.getElementById("emailList");

    function fetchEmails(account, folder, query = "") {
        fetch(`/emails?account=${account}&folder=${folder}&query=${query}`)
            .then(response => response.json())
            .then(data => {
                emailList.innerHTML = "";
                data.forEach(email => {
                    const emailItem = document.createElement("div");
                    emailItem.classList.add("email-item");
                    emailItem.innerHTML = `
                        <div class="email-header">
                            <img src="${email.profile_image || 'default.png'}" alt="Profile" class="profile-pic">
                            <div class="email-info">
                                <strong>${email.sender}</strong>
                                <span>${email.subject}</span>
                            </div>
                            <div class="email-time">${email.time}</div>
                        </div>
                        <div class="email-content">${email.snippet}</div>
                    `;
                    emailItem.addEventListener("click", () => openEmail(email.id));
                    emailList.appendChild(emailItem);
                });
            });
    }

    function openEmail(emailId) {
        window.location.href = `/email/${emailId}`;
    }

    accountSelector.addEventListener("change", () => {
        const selectedAccount = accountSelector.value;
        const activeFolder = document.querySelector("#folderList .active").dataset.folder;
        fetchEmails(selectedAccount, activeFolder);
    });

    folderList.addEventListener("click", (event) => {
        if (event.target.tagName === "LI") {
            document.querySelector("#folderList .active")?.classList.remove("active");
            event.target.classList.add("active");
            fetchEmails(accountSelector.value, event.target.dataset.folder);
        }
    });

    searchButton.addEventListener("click", () => {
        fetchEmails(accountSelector.value, document.querySelector("#folderList .active").dataset.folder, searchBar.value);
    });

    // Initial fetch of emails
    fetchEmails("all", "inbox");
});
