// Notifications.js - Handles notification counters and refreshing

document.addEventListener('DOMContentLoaded', function() {
    // Only run this code if the user is logged in (check for notification elements)
    const notificationCountElements = document.querySelectorAll('.notification-count');
    if (notificationCountElements.length === 0) {
        return;
    }

    // Function to fetch the current notification count
    function fetchNotificationCount() {
        fetch('/notifications/count')
            .then(response => response.json())
            .then(data => {
                updateNotificationBadges(data.count);
            })
            .catch(error => {
                console.error('Error fetching notification count:', error);
            });
    }

    // Function to update notification badges in the UI
    function updateNotificationBadges(count) {
        notificationCountElements.forEach(element => {
            if (count > 0) {
                element.textContent = count;
                element.classList.remove('d-none');
            } else {
                element.classList.add('d-none');
            }
        });

        // Update the page title if unread notifications exist
        const originalTitle = document.title.replace(/^\(\d+\) /, '');
        if (count > 0) {
            document.title = `(${count}) ${originalTitle}`;
        } else {
            document.title = originalTitle;
        }
    }

    // Initial fetch
    fetchNotificationCount();

    // Set up periodic refresh every 60 seconds
    setInterval(fetchNotificationCount, 60000);
});
