
import click

def click_parse_range(value, upper_bound):
    """value_proc function to convert the given input to a list of indexes"""
    if value.startswith('a'):
        return range(upper_bound)

    if value.startswith('n'):
        return []

    indexes = []

    try:
        for spec in value.replace(' \t', '').split(','):
            try:
                begin, end = spec.split('-')
            except ValueError:
                indexes.append(int(spec) - 1)
            else:
                indexes += list(range(int(begin) - 1, int(end)))

    except ValueError:
        raise click.BadParameter("Invalid range or value specified", param=value)

    if max(indexes) >= upper_bound:
        raise click.BadParameter("Specified index is out of range", param=max(indexes))

    return sorted(set(indexes))
