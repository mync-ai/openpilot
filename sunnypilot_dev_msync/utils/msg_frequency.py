import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import time
import cereal.messaging as messaging


# Available message topics to test
available_topics = ['carState', 'carControl', 'modelV2', 'longitudinalPlan', 'radarState']

def measure_message_frequency(topic, duration=10.0):
    """
    Measure the frequency of updates for a specific message topic.

    Args:
        topic: The message topic to monitor (e.g., 'modelV2', 'carState')
        duration: How long to measure in seconds

    Returns:
        tuple: (average_frequency, total_updates, time_elapsed)
    """

    if topic not in available_topics:
        print(f"Warning: '{topic}' is not in the list of known topics: {available_topics}")
        print("Proceeding anyway in case it's a valid topic...")

    print(f"Measuring frequency of '{topic}' for {duration} seconds...")

    # Subscribe to the single topic
    sm = messaging.SubMaster([topic])

    update_count = 0
    start_time = time.time()
    last_update_time = start_time

    while True:
        sm.update()
        current_time = time.time()

        # Check if the topic was updated
        if sm.updated[topic]:
            update_count += 1
            time_since_last = current_time - last_update_time
            last_update_time = current_time

            # Print real-time info
            elapsed = current_time - start_time
            current_freq = update_count / elapsed if elapsed > 0 else 0
            print(f"Updates: {update_count:4d} | Elapsed: {elapsed:6.2f}s | Freq: {current_freq:6.2f} Hz", end='\r')

        # Check if duration has elapsed
        if current_time - start_time >= duration:
            break

        # Small sleep to prevent excessive CPU usage
        time.sleep(0.001)

    total_time = time.time() - start_time
    average_frequency = update_count / total_time if total_time > 0 else 0

    print()  # New line after the real-time updates
    print(f"Measurement complete!")
    print(f"Total updates: {update_count}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average frequency: {average_frequency:.2f} Hz")

    return average_frequency, update_count, total_time


def test_multiple_topics(topics, duration=10.0):
    """
    Test frequency for multiple topics sequentially.

    Args:
        topics: List of topics to test
        duration: Duration to test each topic
    """
    results = {}

    for topic in topics:
        print(f"\n{'='*50}")
        print(f"Testing topic: {topic}")
        print(f"{'='*50}")

        try:
            freq, updates, time_elapsed = measure_message_frequency(topic, duration)
            results[topic] = {
                'frequency': freq,
                'updates': updates,
                'time': time_elapsed
            }
        except Exception as e:
            print(f"Error testing {topic}: {e}")
            results[topic] = None

    print(f"\n{'='*50}")
    print("SUMMARY OF ALL TOPICS")
    print(f"{'='*50}")

    for topic, result in results.items():
        if result:
            print(f"{topic:15s}: {result['frequency']:8.2f} Hz ({result['updates']:4d} updates)")
        else:
            print(f"{topic:15s}: ERROR")


if __name__ == "__main__":
    # Test configuration
    test_duration = 10.0  # seconds

    # Option 1: Test a single topic
    single_topic = 'modelV2'  # Change this to test different topics

    # Option 2: Test multiple topics
    topics_to_test = ['modelV2', 'carState', 'carControl']

    print("Message Frequency Tester")
    print("Available topics:", available_topics)
    print()

    # Uncomment one of the following options:

    # Single topic test
    print("Testing single topic...")
    measure_message_frequency(single_topic, test_duration)

    # Multiple topics test (uncomment to use)
    # print("Testing multiple topics...")
    # test_multiple_topics(topics_to_test, test_duration)