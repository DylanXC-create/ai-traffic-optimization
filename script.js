document.addEventListener("DOMContentLoaded", () => {
    console.log("Website loaded. Ready for traffic data.");
    updateData(); // Initial load with default filter

    const content = document.querySelector(".content");
    if (content) {
        setTimeout(() => {
            content.classList.add("loaded");
        }, 500);
    }
});

// Function to toggle the intersections dropdown
function toggleIntersections(header) {
    const intersections = header.nextElementSibling;
    const arrow = header.querySelector(".arrow");
    intersections.classList.toggle("show");
    arrow.classList.toggle("down");
}

// Function to update data based on filter selection
function updateData() {
    const filterSelect = document.getElementById("time-filter");
    const selectedFilter = filterSelect.value;
    const townsContainer = document.getElementById("towns-container");

    fetch(`traffic_results_${selectedFilter}.json`)
        .then(response => response.json())
        .then(data => {
            townsContainer.innerHTML = ""; // Clear existing content
            for (const [town, townData] of Object.entries(data)) {
                const townItem = document.createElement("div");
                townItem.className = "town-item";

                const townHeader = document.createElement("div");
                townHeader.className = "town-header";
                townHeader.onclick = () => toggleIntersections(townHeader);

                const townLink = document.createElement("a");
                townLink.href = "#";
                townLink.textContent = town;
                townHeader.appendChild(townLink);

                const arrow = document.createElement("span");
                arrow.className = "arrow";
                arrow.textContent = "▶";
                townHeader.appendChild(arrow);

                const intersectionsDiv = document.createElement("div");
                intersectionsDiv.className = "intersections";

                for (const intersection of townData.intersections) {
                    const intersectionItem = document.createElement("div");
                    intersectionItem.className = "intersection-item";
                    intersectionItem.textContent = `${intersection.name} - Delay: ${intersection.delay_minutes} min/vehicle, Vehicles: ${intersection.total_vehicles.toLocaleString()}, Time Savings: $${intersection.time_savings_usd.toLocaleString()}, Fuel Savings: $${intersection.fuel_savings_usd.toLocaleString()}`;
                    intersectionsDiv.appendChild(intersectionItem);
                }

                const totalDiv = document.createElement("div");
                totalDiv.className = "intersection-item";
                totalDiv.textContent = `Town Total Savings: $${(townData.total_time_savings + townData.total_fuel_savings).toLocaleString()}`;
                intersectionsDiv.appendChild(totalDiv);

                const xaiAnalysisDiv = document.createElement("div");
                xaiAnalysisDiv.className = "xai-analysis";
                xaiAnalysisDiv.textContent = `xAI Analysis: ${townData.xai_analysis}`;
                intersectionsDiv.appendChild(xaiAnalysisDiv);

                townItem.appendChild(townHeader);
                townItem.appendChild(intersectionsDiv);
                townsContainer.appendChild(townItem);
            }
        })
        .catch(error => console.error("Error loading data:", error));
}