document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const messageDiv = document.getElementById("message");
  const loginToggle = document.getElementById("teacher-login-toggle");
  const loginForm = document.getElementById("login-form");
  const logoutButton = document.getElementById("teacher-logout");
  const teacherStatus = document.getElementById("teacher-status");

  let isTeacher = false;
  let authConfigured = false;

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function renderTeacherControls(username = "") {
    signupContainer.hidden = !isTeacher;
    loginToggle.hidden = isTeacher || !authConfigured;
    loginForm.classList.add("hidden");
    loginToggle.setAttribute("aria-expanded", "false");
    logoutButton.classList.toggle("hidden", !isTeacher);
    teacherStatus.textContent = isTeacher
      ? `Signed in as ${username}`
      : authConfigured
        ? ""
        : "Teacher access is not configured.";
  }

  async function fetchAuthState() {
    const response = await fetch("/auth/me");
    const authState = await response.json();
    if (!response.ok) {
      throw new Error(authState.detail || "Could not check teacher login status.");
    }

    authConfigured = authState.configured;
    isTeacher = authState.authenticated;
    renderTeacherControls(authState.username);
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("The activities could not be loaded.");
      }
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.innerHTML =
        '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
                <h5>Participants:</h5>
                <ul class="participants-list">
                  ${details.participants
                    .map(
                      (email) => `<li>
                        <span class="participant-email">${escapeHTML(email)}</span>
                        ${
                          isTeacher
                            ? `<button class="delete-btn" data-activity="${escapeHTML(name)}" data-email="${escapeHTML(email)}" aria-label="Remove ${escapeHTML(email)} from ${escapeHTML(name)}">❌</button>`
                            : ""
                        }
                      </li>`
                    )
                    .join("")}
                </ul>
              </div>`
            : "<p><em>No participants yet</em></p>";

        activityCard.innerHTML = `
          <h4>${escapeHTML(name)}</h4>
          <p>${escapeHTML(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHTML(details.schedule)}</p>
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

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "An error occurred.");
      }

      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  async function handleSignup(event) {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "An error occurred.");
      }

      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      showMessage(error.message || "Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  }

  loginToggle.addEventListener("click", () => {
    const willOpen = loginForm.classList.contains("hidden");
    loginForm.classList.toggle("hidden", !willOpen);
    loginToggle.setAttribute("aria-expanded", String(willOpen));
    if (willOpen) {
      document.getElementById("teacher-username").focus();
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("teacher-username").value;
    const password = document.getElementById("teacher-password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Could not sign in.");
      }

      loginForm.reset();
      await fetchAuthState();
      await fetchActivities();
      showMessage(result.message, "success");
    } catch (error) {
      showMessage(error.message || "Could not sign in.", "error");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Could not sign out.");
      }

      await fetchAuthState();
      await fetchActivities();
      showMessage(result.message, "success");
    } catch (error) {
      showMessage(error.message || "Could not sign out.", "error");
      console.error("Error signing out:", error);
    }
  });

  signupForm.addEventListener("submit", handleSignup);

  fetchAuthState()
    .catch((error) => {
      isTeacher = false;
      authConfigured = false;
      renderTeacherControls();
      teacherStatus.textContent = "Could not verify teacher access.";
      console.error("Error checking teacher login:", error);
      showMessage(error.message || "Could not verify teacher login.", "error");
    })
    .finally(fetchActivities);
});
