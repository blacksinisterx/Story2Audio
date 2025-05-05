import requests
import time
import threading
import csv
import os
import matplotlib.pyplot as plt
import psutil
import GPUtil
from datetime import datetime

# Configuration for the FastAPI backend
API_URL = "http://localhost:5000/story-to-audio"  # Your FastAPI endpoint
NUM_REQUESTS = [2,7,12,22]  # Total number of requests to send per concurrency level
CONCURRENCY_LEVELS = [1, 5, 10, 20]  # Different concurrency levels to test

# Test data with different storylines and genres
TEST_SCENARIOS = [
    {"storyline": "A brave knight embarks on a quest to save the kingdom", "genre": "Fantasy"},
    {"storyline": "Two scientists discover a portal to another dimension", "genre": "Sci-Fi"},
    {"storyline": "A detective investigates a series of mysterious disappearances", "genre": "Mystery"},
    {"storyline": "A young woman travels the world seeking adventure", "genre": "Adventure"},
    {"storyline": "Ghostly apparitions begin haunting an old mansion", "genre": "Horror"}
]

# Create results directory
RESULTS_DIR = "performance_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Generate timestamp for this test run
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILE = os.path.join(RESULTS_DIR, f"performance_log_{TIMESTAMP}.csv")
SUMMARY_FILE = os.path.join(RESULTS_DIR, f"performance_summary_{TIMESTAMP}.csv")
PLOT_FILE = os.path.join(RESULTS_DIR, f"performance_plot_{TIMESTAMP}.png")

# Class to monitor system resources
class ResourceMonitor:
    def __init__(self, interval=1.0):
        self.interval = interval
        self.running = False
        self.cpu_percentages = []
        self.memory_percentages = []
        self.gpu_percentages = []
        self.monitor_thread = None

    def start(self):
        self.running = True
        self.cpu_percentages = []
        self.memory_percentages = []
        self.gpu_percentages = []
        self.monitor_thread = threading.Thread(target=self._monitor)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        # Calculate averages
        avg_cpu = sum(self.cpu_percentages) / len(self.cpu_percentages) if self.cpu_percentages else 0
        avg_memory = sum(self.memory_percentages) / len(self.memory_percentages) if self.memory_percentages else 0
        avg_gpu = sum(self.gpu_percentages) / len(self.gpu_percentages) if self.gpu_percentages else 0
        
        return {
            "cpu_usage": avg_cpu,
            "memory_usage": avg_memory,
            "gpu_usage": avg_gpu
        }

    def _monitor(self):
        while self.running:
            # CPU usage
            self.cpu_percentages.append(psutil.cpu_percent(interval=None))
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_percentages.append(memory.percent)
            
            # GPU usage (if available)
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    # Use the first GPU if multiple are available
                    self.gpu_percentages.append(gpus[0].load * 100)
                else:
                    self.gpu_percentages.append(0)
            except Exception:
                self.gpu_percentages.append(0)
            
            time.sleep(self.interval)

# Function to send a request to the API
def send_request(request_id, results_list, lock):
    # Get test data (cycle through scenarios if more requests than scenarios)
    scenario = TEST_SCENARIOS[request_id % len(TEST_SCENARIOS)]
    
    payload = {
        "storyline": scenario["storyline"],
        "genre": scenario["genre"]
    }
    
    print(f"Request {request_id}: Sending {scenario['genre']} storyline...")
    
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=800)
        elapsed_time = time.time() - start_time
        
        status_code = response.status_code
        print(f"Request {request_id} completed: Status {status_code}, Time {elapsed_time:.2f}s")
        
        # Store the results
        with lock:
            results_list.append({
                "request_id": request_id,
                "response_time": elapsed_time,
                "status_code": status_code,
                "genre": scenario["genre"],
                "response_preview": response.json().get("story", "")[:50] if status_code == 200 else "Error"
            })
        
    except requests.exceptions.RequestException as e:
        print(f"Error in request {request_id}: {str(e)}")
        
        # Store the error results
        with lock:
            results_list.append({
                "request_id": request_id,
                "response_time": -1,  # Use -1 to indicate error
                "status_code": 0,
                "genre": scenario["genre"],
                "response_preview": str(e)
            })

# Function to run tests with a specific concurrency level
def run_concurrency_test(concurrency, num_requests):
    print(f"\n--- Starting test with concurrency level: {concurrency} ---")
    
    # Results container
    results = []
    lock = threading.Lock()
    
    # Start resource monitor
    monitor = ResourceMonitor(interval=0.5)
    monitor.start()
    
    # Create and start threads
    threads = []
    for i in range(num_requests):
        thread = threading.Thread(target=send_request, args=(i+1, results, lock))
        threads.append(thread)
    
    # Start threads with controlled concurrency
    active_threads = []
    for thread in threads:
        thread.start()
        active_threads.append(thread)
        
        # If we've reached max concurrency, wait for one to finish
        if len(active_threads) >= concurrency:
            active_threads[0].join()
            active_threads.pop(0)
    
    # Wait for any remaining threads
    for thread in active_threads:
        thread.join()
    
    # Stop resource monitor and get metrics
    resource_metrics = monitor.stop()
    
    # Calculate response time statistics
    successful_times = [r["response_time"] for r in results if r["response_time"] > 0]
    avg_response_time = sum(successful_times) / len(successful_times) if successful_times else 0
    
    # Success rate
    success_count = sum(1 for r in results if r["status_code"] == 200)
    success_rate = (success_count / len(results)) * 100 if results else 0
    
    print(f"Concurrency {concurrency} completed: Avg time {avg_response_time:.2f}s, Success rate {success_rate:.1f}%")
    
    # Save detailed results to CSV
    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        for r in results:
            writer.writerow([
                concurrency,
                r["request_id"], 
                r["response_time"], 
                r["status_code"], 
                r["genre"], 
                r["response_preview"]
            ])
    
    return {
        "concurrency": concurrency,
        "avg_response_time": avg_response_time,
        "success_rate": success_rate,
        "cpu_usage": resource_metrics["cpu_usage"],
        "memory_usage": resource_metrics["memory_usage"],
        "gpu_usage": resource_metrics["gpu_usage"]
    }

# Generate performance report
def generate_performance_report(summary_results):
    print("\nGenerating performance report...")
    
    # Create the plot
    fig, ax = plt.subplots(2, 2, figsize=(15, 10))
    
    # Extract data for plotting
    concurrency_levels = [r["concurrency"] for r in summary_results]
    avg_times = [r["avg_response_time"] for r in summary_results]
    cpu_usages = [r["cpu_usage"] for r in summary_results]
    memory_usages = [r["memory_usage"] for r in summary_results]
    gpu_usages = [r["gpu_usage"] for r in summary_results]
    
    # Plot 1: Response times
    ax[0, 0].plot(concurrency_levels, avg_times, 'o-', linewidth=2)
    ax[0, 0].set_xlabel('Concurrent Requests')
    ax[0, 0].set_ylabel('Avg Response Time (seconds)')
    ax[0, 0].set_title('Response Time vs Concurrency')
    ax[0, 0].grid(True)
    
    # Plot 2: CPU usage
    ax[0, 1].plot(concurrency_levels, cpu_usages, 'o-', linewidth=2, color='green')
    ax[0, 1].set_xlabel('Concurrent Requests')
    ax[0, 1].set_ylabel('CPU Usage (%)')
    ax[0, 1].set_title('CPU Usage vs Concurrency')
    ax[0, 1].grid(True)
    
    # Plot 3: Memory usage
    ax[1, 0].plot(concurrency_levels, memory_usages, 'o-', linewidth=2, color='red')
    ax[1, 0].set_xlabel('Concurrent Requests')
    ax[1, 0].set_ylabel('Memory Usage (%)')
    ax[1, 0].set_title('Memory Usage vs Concurrency')
    ax[1, 0].grid(True)
    
    # Plot 4: GPU usage
    ax[1, 1].plot(concurrency_levels, gpu_usages, 'o-', linewidth=2, color='purple')
    ax[1, 1].set_xlabel('Concurrent Requests')
    ax[1, 1].set_ylabel('GPU Usage (%)')
    ax[1, 1].set_title('GPU Usage vs Concurrency')
    ax[1, 1].grid(True)
    
    plt.tight_layout()
    plt.savefig(PLOT_FILE)
    print(f"Performance plot saved to: {PLOT_FILE}")
    
    # Create a pretty-printed table for the terminal
    print("\n=== PERFORMANCE SUMMARY ===")
    print(f"{'Concurrency':<12} | {'Avg Time (s)':<12} | {'CPU (%)':<8} | {'Mem (%)':<8} | {'GPU (%)':<8}")
    print("-" * 60)
    for r in summary_results:
        print(f"{r['concurrency']:<12} | {r['avg_response_time']:<12.2f} | {r['cpu_usage']:<8.1f} | {r['memory_usage']:<8.1f} | {r['gpu_usage']:<8.1f}")

if __name__ == "__main__":
    # Create CSV file with headers
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Concurrency", "Request ID", "Response Time (s)", "Status Code", "Genre", "Response Preview"])
    
    # Create summary CSV file with headers
    with open(SUMMARY_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Concurrency", "Avg Response Time (s)", "Success Rate (%)", "CPU Usage (%)", "Memory Usage (%)", "GPU Usage (%)"])
    
    print(f"Starting benchmark tests with concurrency levels: {CONCURRENCY_LEVELS}")
    print(f"Results will be saved to {RESULTS_DIR}")
    
    # Run tests for each concurrency level
    summary_results = []
    
    for i,concurrency in enumerate(CONCURRENCY_LEVELS):
        result = run_concurrency_test(concurrency, NUM_REQUESTS[i])
        summary_results.append(result)
        
        # Add to summary CSV
        with open(SUMMARY_FILE, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                result["concurrency"],
                result["avg_response_time"],
                result["success_rate"],
                result["cpu_usage"],
                result["memory_usage"],
                result["gpu_usage"]
            ])
    
    # Generate the final report
    generate_performance_report(summary_results)
    
    print(f"\nPerformance benchmark complete! Results saved to {RESULTS_DIR} directory.")