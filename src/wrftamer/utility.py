import random
import string


def get_random_string(length: int):
    if length < 1:
        raise ValueError

    # generates a ranom string of <length>. Used for unique filenames.
    letters = string.ascii_lowercase  # choose from all lowercase letter
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str
