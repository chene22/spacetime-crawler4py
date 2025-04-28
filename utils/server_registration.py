import os
from spacetime import Node
from utils.pcc_models import Register

def init(df, user_agent, fresh):
    reg = df.read_one(Register, user_agent)
    if not reg:
        reg = Register(user_agent, fresh)
        df.add_one(Register, reg)
        df.commit()
        df.push_await()
    while not reg.load_balancer:
        print("Inside while loop inside server_registration.py init")
        df.pull_await()
        print("Passed df.pull_await()")
        if reg.invalid:
            raise RuntimeError("User agent string is not acceptable.")
        if reg.load_balancer:
            print("reg.load_balancer is true")
            df.delete_one(Register, reg)
            df.commit()
            df.push()
            print("df has been committed and pushed")
    print("Finished server_registration.py init; returning reg.load_balancer")
    return reg.load_balancer

def get_cache_server(config, restart):
    print("Starting get_cache_server");
    init_node = Node(
        init, Types=[Register], dataframe=(config.host, config.port))
    print("We have defined init_node")
    return init_node.start(
        config.user_agent, restart or not os.path.exists(config.save_file))