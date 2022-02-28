model = am.Model(
    components=['Benzene', 'Toluene'],
    F=100., # kmol/h
    P=112000, # Pa
    P_drop = 0, # Pa
    z_feed = [0.7, 0.3],
    E = [1. for i in range(36)],
    RR=0.924,
    D=63.636,
    N=34,
    feed_stage=22,
)