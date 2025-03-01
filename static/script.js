document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM fully loaded");

    const accountSelector = document.getElementById("accountSelector");
    const folderList = document.getElementById("folderList");
    const searchBar = document.getElementById("searchBar");
    const searchButton = document.getElementById("searchButton");
    const emailList = document.getElementById("emailList");

    let selectedCategory = "inbox";  // Default category

    if (!accountSelector) {
        console.error("Error: 'accountSelector' not found in the DOM.");
        return;
    }

    function populateAccountDropdown() {
        fetch("/accounts")
            .then(response => response.json())
            .then(accounts => {
                console.log("Fetched Accounts:", accounts);  // Debugging
                accountSelector.innerHTML = '<option value="all">All Accounts</option>';
                accounts.forEach(account => {
                    const option = document.createElement("option");
                    option.value = account.email;
                    option.textContent = account.email;
                    accountSelector.appendChild(option);
                });
            })
            .catch(error => console.error("Error fetching accounts:", error));
    }

    function fetchEmails(account = "all", category = "inbox", query = "") {
        let url = query
            ? `/search?q=${encodeURIComponent(query)}&account=${account}&category=${category}`
            : `/emails?account=${account}&category=${category}`;

        console.log("Fetching emails from:", url); // Debugging

        fetch(url)
            .then(response => response.json())
            .then(data => {
                emailList.innerHTML = "";  // Clear list before adding new emails

                if (data.length === 0) {
                    emailList.innerHTML = "<p>No emails found.</p>";
                    return;
                }

                data.forEach(email => {
                    const emailItem = document.createElement("div");
                    emailItem.classList.add("email-item");
                    emailItem.innerHTML = `
                        <div class="email-header">
                            <img src="${email.profile_image || '/static/profile.jpg'}" alt="Profile" class="profile-pic">
                            <div class="email-info">
                                <strong>${email["from"] || "Unknown Sender"}</strong>  
                                <span>${email.subject || "No Subject"}</span>  
                            </div>
                            <div class="email-time">${email.date || "No Date"}</div>  
                            <div class="email-category">${email.category || "Uncategorized"}</div>  
                        </div>
                        <div class="email-content">${email.body || "No Content Available"}</div> 
                    `;

                    emailList.appendChild(emailItem);
                });
            })
            .catch(error => console.error("Error fetching emails:", error));
    }

    function openEmail(emailId) {
        if (emailId) {
            window.location.href = `/email/${emailId}`;
        } else {
            console.error("Email ID is missing.");
        }
    }

    // Handle category clicks from the left sidebar
    folderList.addEventListener("click", (event) => {
        if (event.target.tagName === "LI") {
            document.querySelector("#folderList .active")?.classList.remove("active");
            event.target.classList.add("active");

            selectedCategory = event.target.dataset.folder;
            fetchEmails(accountSelector.value, selectedCategory);
        }
    });

    // Handle account selection change
    accountSelector.addEventListener("change", () => {
        const selectedAccount = accountSelector.value;
        console.log("Selected Account:", selectedAccount); // Debugging
        fetchEmails(selectedAccount, selectedCategory);
    });

    // Handle search
    if (searchButton) {
        searchButton.addEventListener("click", () => {
            fetchEmails(accountSelector.value, selectedCategory, searchBar.value);
        });
    } else {
        console.error("Error: 'searchButton' not found in the DOM.");
    }

    // Populate account dropdown and load initial emails
    populateAccountDropdown();
    fetchEmails();
});