import random
import string


def get_random_string(length: int):
    if length < 1:
        raise ValueError

    # generates a ranom string of <length>. Used for unique filenames.
    letters = string.ascii_lowercase  # choose from all lowercase letter
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str


def permute_dict_of_dicts_order(in_dict: dict) -> dict:
    """
    This function assumes that in_dict is a dictionary of dictionaries and reverses the order of keys, which is
    handy in some cases.


    Args:
        in_dict: a dictionary of dictionaries (i.e. name_of_dict[key1][key2])

    Returns: the same dictionary with permute key order (i.e. name_of_dict[key2][key1])

    TODO: write a test.

    """

    keys1 = in_dict.keys()
    keys2 = in_dict[list(keys1)[0]].keys()

    new_dict = dict()
    for key2 in keys2:
        new_dict[key2] = dict()
        for key1 in keys1:
            new_dict[key2][key1] = in_dict[key1][key2]

    return new_dict
