// javascript for making the webpage interactive
document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM fully loaded");

    const accountSelector = document.getElementById("accountSelector");
    const folderList = document.getElementById("folderList");
    const searchBar = document.getElementById("searchBar");
    const searchButton = document.getElementById("searchButton");
    const emailList = document.getElementById("emailList");

    let selectedCategory = "inbox";

    if (!accountSelector) {
        console.error("Error: 'accountSelector' not found in the DOM.");
        return;
    }

    function sanitizeHTML(html) {
        let tempDiv = document.createElement("div");
        tempDiv.innerHTML = html;
        return tempDiv.textContent || tempDiv.innerText || "";
    }

    function populateAccountDropdown() {
        fetch("/accounts")
            .then(response => response.json())
            .then(accounts => {
                console.log("Fetched Accounts:", accounts);
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


function decodeEmailSubject(encodedSubject) {
    try {
        return decodeURIComponent(escape(atob(encodedSubject.split("?B?")[1].split("?=")[0])));
    } catch (error) {
        return encodedSubject;
    }
}
// function removeStyles(html) {
//     return html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "");  // Removes all <style> tags
// }
    function fetchEmails(account = "all", folder = "inbox", query = "") {
        let url = query
            ? `/search?q=${encodeURIComponent(query)}&account=${account}&category=${folder}`
            : `/emails?account=${account}&category=${folder}`;

        console.log("Fetching emails from:", url);

        fetch(url)
            .then(response => response.json())
            .then(data => {
                emailList.innerHTML = ""; // Clear list

                if (data.length === 0) {
                    emailList.innerHTML = "<p>No emails found.</p>";
                    return;
                }

                data.forEach(email => {
                    // let cleanBody = removeStyles(email.body);
                    let displayCategory = email.ai_category || "Uncategorized";

                    const emailItem = document.createElement("div");
                    emailItem.classList.add("email-item");
                    emailItem.innerHTML = `
                        <div class="email-header">
                            <img src="${email.profile_image || '/static/profile.jpg'}" alt="Profile" class="profile-pic">
                            <div class="email-info">
                                <strong>${email["from"] || "Unknown Sender"}</strong>  
                                <span>${decodeEmailSubject(email.subject) || "No Subject"}</span>  
 
                            </div>
                            <div class="email-time">${email.date || "No Date"}</div>  
                            ${displayCategory ? `<div class="email-category">${displayCategory}</div>` : ""}
                        </div>
                        <div class="email-content">${email.body ? email.body : "No Content Available"}</div>                            
                    `;

                    emailList.appendChild(emailItem);

                });
                document.getElementById(`email-body-${email.id}`).textContent = email.body;
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

    folderList.addEventListener("click", (event) => {
        if (event.target.tagName === "LI") {
            document.querySelector("#folderList .active")?.classList.remove("active");
            event.target.classList.add("active");

            selectedCategory = event.target.dataset.folder;
            fetchEmails(accountSelector.value, selectedCategory);
        }
    });

    accountSelector.addEventListener("change", () => {
        const selectedAccount = accountSelector.value;
        console.log("Selected Account:", selectedAccount);
        fetchEmails(selectedAccount, selectedCategory);
    });

    if (searchButton) {
        searchButton.addEventListener("click", () => {
            fetchEmails(accountSelector.value, selectedCategory, searchBar.value);
        });
    } else {
        console.error("Error: 'searchButton' not found in the DOM.");
    }

    populateAccountDropdown();
    fetchEmails();
});
