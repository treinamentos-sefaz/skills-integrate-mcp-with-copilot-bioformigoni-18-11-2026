document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupContainer = document.getElementById("signup-container");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const adminStatus = document.getElementById("admin-status");
  const adminUsername = document.getElementById("admin-username");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");
  const closeLoginButton = document.getElementById("close-login-button");
  let currentTeacher = null;

  function escapeHtml(value) {
    const element = document.createElement("span");
    element.textContent = value;
    return element.innerHTML;
  }

  function showMessage(text, type, element = messageDiv) {
    element.textContent = text;
    element.className = type;
    element.classList.remove("hidden");
  }

  function hideMessageLater(element = messageDiv) {
    setTimeout(() => element.classList.add("hidden"), 5000);
  }

  function updateAdminUI() {
    const isAdmin = currentTeacher !== null;
    loginButton.classList.toggle("hidden", isAdmin);
    adminStatus.classList.toggle("hidden", !isAdmin);
    signupContainer.classList.toggle("hidden", !isAdmin);
    adminUsername.textContent = isAdmin ? `Logged in as ${currentTeacher}` : "";
  }

  async function fetchSession() {
    try {
      const response = await fetch("/admin/session");
      if (response.ok) {
        const session = await response.json();
        currentTeacher = session.username;
      } else {
        currentTeacher = null;
      }
    } catch (error) {
      currentTeacher = null;
      console.error("Error checking teacher session:", error);
    }
    updateAdminUI();
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Unable to load activities");
      }
      const activities = await response.json();
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const spotsLeft = details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li>
                        <span class="participant-email">${escapeHtml(email)}</span>
                        ${
                          currentTeacher
                            ? `<button class="delete-btn" data-activity="${escapeHtml(
                                name
                              )}" data-email="${escapeHtml(email)}">❌</button>`
                            : ""
                        }
                      </li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : "<p><em>No participants yet</em></p>";

        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document
        .querySelectorAll(".delete-btn")
        .forEach((button) => button.addEventListener("click", handleUnregister));
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          button.dataset.activity
        )}/unregister?email=${encodeURIComponent(button.dataset.email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 401) {
          currentTeacher = null;
          updateAdminUI();
        }
        throw new Error(result.detail || "An error occurred");
      }

      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
    hideMessageLater();
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(
          email
        )}`,
        { method: "POST" }
      );
      const result = await response.json();
      if (!response.ok) {
        if (response.status === 401) {
          currentTeacher = null;
          updateAdminUI();
          await fetchActivities();
        }
        throw new Error(result.detail || "An error occurred");
      }

      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
    hideMessageLater();
  });

  loginButton.addEventListener("click", () => {
    loginMessage.classList.add("hidden");
    loginDialog.showModal();
  });

  closeLoginButton.addEventListener("click", () => loginDialog.close());

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const credentials = {
      username: document.getElementById("username").value,
      password: document.getElementById("password").value,
    };

    try {
      const response = await fetch("/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to log in");
      }

      currentTeacher = result.username;
      loginForm.reset();
      loginDialog.close();
      updateAdminUI();
      await fetchActivities();
    } catch (error) {
      showMessage(error.message, "error", loginMessage);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/admin/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to log out");
      }
      currentTeacher = null;
      updateAdminUI();
      await fetchActivities();
    } catch (error) {
      showMessage(error.message, "error");
      hideMessageLater();
    }
  });

  async function initialize() {
    await fetchSession();
    await fetchActivities();
  }

  initialize();
});
