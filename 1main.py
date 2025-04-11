import heapq
from collections import defaultdict
import customtkinter as ctk
from tkinter import messagebox, END
import time
import random
import json
import os

DISTANCE_JSON_FILE = "distances.json"


def update_distance_json(city1, city2, distance):
    data = {}
    if os.path.exists(DISTANCE_JSON_FILE):
        with open(DISTANCE_JSON_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}

    if city1 not in data:
        data[city1] = {}
    if city2 not in data:
        data[city2] = {}

    data[city1][city2] = distance
    data[city2][city1] = distance  # Keep it bidirectional

    with open(DISTANCE_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class Graph:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, city1, city2, road_distance):
        self.remove_edge(city1, city2)
        self.graph[city1].append((city2, road_distance))
        self.graph[city2].append((city1, road_distance))
        update_distance_json(city1, city2, road_distance)

    def remove_edge(self, city1, city2):
        self.graph[city1] = [edge for edge in self.graph[city1] if edge[0] != city2]
        self.graph[city2] = [edge for edge in self.graph[city2] if edge[0] != city1]

    def dijkstra(self, start, animate_func=None):
        distances = {city: float("inf") for city in self.graph}
        distances[start] = 0
        pq = [(0, start)]
        previous_nodes = {city: None for city in self.graph}
        visited = set()

        while pq:
            current_distance, current_city = heapq.heappop(pq)

            if current_city in visited:
                continue

            visited.add(current_city)

            if animate_func:
                animate_func(current_city, visited, previous_nodes, distances)

            for neighbor, road_distance in self.graph[current_city]:
                if neighbor in visited:
                    continue
                new_distance = current_distance + road_distance
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous_nodes[neighbor] = current_city
                    heapq.heappush(pq, (new_distance, neighbor))

        return distances, previous_nodes

    def get_distance_between(self, city1, city2):
        for neighbor, distance in self.graph[city1]:
            if neighbor == city2:
                return distance
        return None

    def shortest_distance_between(self, city1, city2, animate_func=None):
        if city1 not in self.graph or city2 not in self.graph:
            return float("inf"), []

        distances, previous_nodes = self.dijkstra(city1, animate_func)
        if distances[city2] == float("inf"):
            return float("inf"), []

        path = []
        current_city = city2
        while current_city is not None:
            path.append(current_city)
            current_city = previous_nodes[current_city]

        path.reverse()
        return distances[city2], path


class App:
    def __init__(self, master):
        self.master = master
        self.graph = Graph()
        self.city_positions = {}
        self.selected_start = None
        self.selected_destination = None
        self.search_history = []
        self.master.title("Urban Navigation System")
        self.master.geometry("1000x800")
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.setup_layout()
        self.setup_canvas_bindings()

    def setup_canvas_bindings(self):
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def on_canvas_click(self, event):
        clicked_city = None
        for city, (x, y) in self.city_positions.items():
            if (x - 15 <= event.x <= x + 15) and (y - 15 <= event.y <= y + 15):
                clicked_city = city
                break

        if clicked_city:
            if not self.selected_start:
                self.selected_start = clicked_city
                self.city1_entry.delete(0, END)
                self.city1_entry.insert(0, clicked_city)
                self.canvas.create_text(
                    event.x,
                    event.y - 25,
                    text="Start",
                    fill="green",
                    font=("Arial", 10, "bold"),
                )
            elif not self.selected_destination and clicked_city != self.selected_start:
                self.selected_destination = clicked_city
                self.city2_entry.delete(0, END)
                self.city2_entry.insert(0, clicked_city)
                self.canvas.create_text(
                    event.x,
                    event.y - 25,
                    text="Destination",
                    fill="red",
                    font=("Arial", 10, "bold"),
                )
                self.calculate_shortest_path()
            else:
                self.selected_start = clicked_city
                self.selected_destination = None
                self.city1_entry.delete(0, END)
                self.city1_entry.insert(0, clicked_city)
                self.city2_entry.delete(0, END)
                self.animate_graph()

    def setup_layout(self):
        # Left frame for input
        self.input_frame = ctk.CTkFrame(self.master)
        self.input_frame.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(self.input_frame, text="City 1 (Start):").grid(
            row=0, column=0, padx=10, pady=5
        )
        self.city1_entry = ctk.CTkEntry(self.input_frame, width=200)
        self.city1_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.input_frame, text="City 2 (Destination):").grid(
            row=1, column=0, padx=10, pady=5
        )
        self.city2_entry = ctk.CTkEntry(self.input_frame, width=200)
        self.city2_entry.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.input_frame, text="Distance (km):").grid(
            row=2, column=0, padx=10, pady=5
        )
        self.distance_entry = ctk.CTkEntry(self.input_frame, width=200)
        self.distance_entry.grid(row=2, column=1, padx=10, pady=5)

        self.add_distance_button = ctk.CTkButton(
            self.input_frame,
            text="Add/Update Distance",
            command=self.add_edge,
            fg_color="#4CAF50",
        )
        self.add_distance_button.grid(row=3, columnspan=2, pady=10)

        self.delete_distance_button = ctk.CTkButton(
            self.input_frame,
            text="Delete Distance",
            command=self.delete_edge,
            fg_color="#FF5722",
        )
        self.delete_distance_button.grid(row=4, columnspan=2, pady=5)

        self.calculate_path_button = ctk.CTkButton(
            self.input_frame,
            text="Calculate Shortest Path",
            command=self.calculate_shortest_path,
            fg_color="#2196F3",
        )
        self.calculate_path_button.grid(row=5, columnspan=2, pady=10)

        self.clear_button = ctk.CTkButton(
            self.input_frame,
            text="Clear All",
            command=self.clear_graph,
            fg_color="#FF0000",
        )
        self.clear_button.grid(row=6, columnspan=2, pady=10)

        # Search History Section
        ctk.CTkLabel(
            self.input_frame, text="Search History:", font=ctk.CTkFont(weight="bold")
        ).grid(row=7, columnspan=2, pady=(20, 5))

        self.history_listbox = ctk.CTkTextbox(self.input_frame, height=150, width=200)
        self.history_listbox.grid(row=8, columnspan=2, pady=5)

        self.clear_history_button = ctk.CTkButton(
            self.input_frame,
            text="Clear History",
            command=self.clear_history,
            fg_color="#9E9E9E",
            width=100,
        )
        self.clear_history_button.grid(row=9, columnspan=2, pady=5)

        # Right frame for output and visualization
        self.output_frame = ctk.CTkFrame(self.master)
        self.output_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.instruction_label = ctk.CTkLabel(
            self.output_frame,
            text="Click on cities to select start and destination",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.instruction_label.pack(pady=5)

        self.distances_listbox = ctk.CTkTextbox(
            self.output_frame, height=150, width=300
        )
        self.distances_listbox.pack(pady=10)

        self.result_area = ctk.CTkTextbox(self.output_frame, height=50, width=300)
        self.result_area.pack(pady=10)

        self.canvas = ctk.CTkCanvas(
            self.output_frame, width=800, height=600, bg="light blue"
        )
        self.canvas.pack(pady=10)

    def add_to_history(self, city1, city2, distance, path):
        history_entry = (
            f"{city1} → {city2}: {distance} km\nPath: {' → '.join(path)}\n\n"
        )
        self.search_history.append(history_entry)
        self.update_history_display()

    def update_history_display(self):
        self.history_listbox.delete("1.0", END)
        for entry in reversed(self.search_history):  # Show most recent first
            self.history_listbox.insert(END, entry)

    def clear_history(self):
        self.search_history = []
        self.history_listbox.delete("1.0", END)

    def add_edge(self):
        try:
            city1 = self.city1_entry.get().strip()
            city2 = self.city2_entry.get().strip()
            distance = int(self.distance_entry.get().strip())

            if not city1 or not city2:
                raise ValueError("City names cannot be empty")
            if distance <= 0:
                raise ValueError("Distance must be positive")

            self.graph.add_edge(city1, city2, distance)

            if city1 not in self.city_positions:
                self.city_positions[city1] = self.get_random_position()
            if city2 not in self.city_positions:
                self.city_positions[city2] = self.get_random_position()

            messagebox.showinfo("Success", "Distance added/updated successfully.")
            self.display_distances()
            self.animate_graph()

            self.city1_entry.delete(0, END)
            self.city2_entry.delete(0, END)
            self.distance_entry.delete(0, END)
            self.selected_start = None
            self.selected_destination = None
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def get_random_position(self):
        return random.randint(50, 750), random.randint(50, 550)

    def delete_edge(self):
        city1 = self.city1_entry.get().strip()
        city2 = self.city2_entry.get().strip()

        if not city1 or not city2:
            messagebox.showerror("Error", "Please enter both city names")
            return

        if city1 not in self.graph.graph or city2 not in self.graph.graph:
            messagebox.showerror("Error", "One or both cities not found")
            return

        self.graph.remove_edge(city1, city2)
        messagebox.showinfo("Success", "Distance deleted successfully.")
        self.display_distances()
        self.animate_graph()

    def display_distances(self):
        self.distances_listbox.delete("1.0", END)
        added_edges = set()

        for city, roads in self.graph.graph.items():
            for neighbor, distance in roads:
                edge_key = tuple(sorted((city, neighbor)))
                if edge_key not in added_edges:
                    self.distances_listbox.insert(
                        END, f"{city} <-> {neighbor}: {distance} km\n"
                    )
                    added_edges.add(edge_key)

    def animate_graph(self, highlight_path=None):
        self.canvas.delete("all")

        for city, roads in self.graph.graph.items():
            for neighbor, distance in roads:
                if city in self.city_positions and neighbor in self.city_positions:
                    x1, y1 = self.city_positions[city]
                    x2, y2 = self.city_positions[neighbor]

                    is_path_edge = False
                    if highlight_path:
                        for i in range(len(highlight_path) - 1):
                            if (
                                city == highlight_path[i]
                                and neighbor == highlight_path[i + 1]
                            ) or (
                                city == highlight_path[i + 1]
                                and neighbor == highlight_path[i]
                            ):
                                is_path_edge = True
                                break

                    color = "green" if is_path_edge else "black"
                    width = 3 if is_path_edge else 1
                    self.draw_line(x1, y1, x2, y2, color, distance, width)

        for city, (x, y) in self.city_positions.items():
            is_path_city = (
                highlight_path and city in highlight_path if highlight_path else False
            )
            is_start = city == self.selected_start
            is_dest = city == self.selected_destination

            if is_start:
                fill_color = "green"
            elif is_dest:
                fill_color = "red"
            elif is_path_city:
                fill_color = "orange"
            else:
                fill_color = "yellow"

            self.canvas.create_oval(
                x - 15, y - 15, x + 15, y + 15, fill=fill_color, outline="black"
            )
            self.canvas.create_text(x, y, text=city, font=("Arial", 10))

    def draw_line(self, x1, y1, x2, y2, color, distance, width=1):
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width)
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        self.canvas.create_text(mid_x, mid_y, text=f"{distance} km", font=("Arial", 8))

    def calculate_shortest_path(self):
        city1 = self.city1_entry.get().strip()
        city2 = self.city2_entry.get().strip()

        if not city1 or not city2:
            messagebox.showerror("Error", "Please enter both city names")
            return

        if city1 not in self.graph.graph or city2 not in self.graph.graph:
            messagebox.showerror("Error", "One or both cities not found")
            return

        distance, path = self.graph.shortest_distance_between(
            city1, city2, self.animate_dijkstra_steps
        )

        if distance == float("inf"):
            self.result_area.delete("1.0", END)
            self.result_area.insert(END, f"No path exists between {city1} and {city2}")
        else:
            self.result_area.delete("1.0", END)
            result_text = f"Shortest path: {distance} km\nPath: {' → '.join(path)}"
            self.result_area.insert(END, result_text)
            self.animate_path(path)
            self.add_to_history(city1, city2, distance, path)

    def animate_dijkstra_steps(self, current_city, visited, previous_nodes, distances):
        self.animate_graph()

        for city in visited:
            if city in self.city_positions:
                x, y = self.city_positions[city]
                self.canvas.create_oval(
                    x - 15, y - 15, x + 15, y + 15, fill="blue", outline="black"
                )
                self.canvas.create_text(x, y, text=city, font=("Arial", 10))

        if current_city in self.city_positions:
            x, y = self.city_positions[current_city]
            self.canvas.create_oval(
                x - 15, y - 15, x + 15, y + 15, fill="red", outline="black"
            )
            self.canvas.create_text(x, y, text=current_city, font=("Arial", 10))

        self.master.update()
        time.sleep(0.5)

    def animate_path(self, path):
        for i in range(len(path)):
            self.animate_graph(path[: i + 1])
            self.master.update()
            time.sleep(0.3)

    def clear_graph(self):
        self.graph = Graph()
        self.city_positions = {}
        self.distances_listbox.delete("1.0", END)
        self.result_area.delete("1.0", END)
        self.canvas.delete("all")
        self.city1_entry.delete(0, END)
        self.city2_entry.delete(0, END)
        self.distance_entry.delete(0, END)
        self.selected_start = None
        self.selected_destination = None


if __name__ == "__main__":
    root = ctk.CTk()
    app = App(root)
    root.mainloop()
