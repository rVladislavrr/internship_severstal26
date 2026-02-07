
def create_key_filters(filters):
    return ','.join([f'{k}:{v}' for k, v in sorted(filters.items(), key=lambda item: item[0]) if v is not None])
