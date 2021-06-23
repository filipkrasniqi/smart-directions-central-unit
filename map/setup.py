import itertools

from utils.parser import Parser
import numpy as np
from scipy import ndimage

if __name__ == "__main__":
    #data_path = "/Users/filipkrasniqi/PycharmProjects/smartdirections/assets/"
    parser = Parser().getInstance()
    id_sd = 3

    sd_instance = parser.read_smartdirections_instance(id_sd)
    building = sd_instance.buildings[0]

    building.initRouting()
    building.computeOfflineMapForFloor()

    start = building.anchors[2][0]
    destination = building.pois[2][0]

    is_v2 = False
    is_v3 = True

    if is_v2:
        # TODO c'è un problema nel computePathList: distances sono tutte inf, why???
        effector_to_activate, face_to_show, relative_message_to_show = building.toActivate(start, destination)
        print("FIRST TEST: \nGoing from {} to {}, first effector: {}\n\n".format(start, destination, effector_to_activate))

        start_points = building.raw_anchors()
        destination_points = building.raw_pois()

        print("REMAINING TESTS\n\n")
        for start, destination in itertools.product(*[start_points, destination_points]):
            effector_to_activate, face_to_show, relative_message_to_show = building.toActivate(start, destination)
            print("Going from {} to {}, first effector: {}.\nFace: {}, direction: {}\n\n".format(start, destination, effector_to_activate, face_to_show, relative_message_to_show))
    elif is_v3:

        # key: origin, val: {destination: list(anchors)}
        tuples_to_check = {
            building.pois[0][0]: {
                building.pois[1][0]: [
                    building.anchors[0][0],
                    building.anchors[1][0],
                    building.anchors[1][1]
                ],
                building.pois[2][0]: [
                    building.anchors[0][0],
                    building.anchors[1][0],
                    building.anchors[1][1],
                    building.anchors[2][0],
                    building.anchors[2][1]
                ]
            },
            building.pois[1][0]: {
                building.pois[0][0]: [
                    building.anchors[1][1],
                    building.anchors[1][0],
                    building.anchors[0][0]
                ],
                building.pois[2][0]: [
                    building.anchors[1][1],
                    building.anchors[2][0],
                    building.anchors[2][1]
                ]
            },
            building.pois[2][0]: {
                building.pois[0][0]: [
                    building.anchors[2][1],
                    building.anchors[2][0],
                    building.anchors[1][1],
                    building.anchors[1][0],
                    building.anchors[0][0]
                ],
                building.pois[1][0]: [
                    building.anchors[2][1],
                    building.anchors[2][0],
                    building.anchors[1][1]
                ]
            }
        }
        for origin in tuples_to_check.keys():
            for destination in tuples_to_check[origin].keys():
                for anchor in tuples_to_check[origin][destination]:
                    effector_to_activate, face_to_show, relative_message_to_show = building.toActivate(anchor, destination, origin)
                    print("Starting from {}, "
                          "localized in {}, "
                          "going to {}.\n "
                          "First effector: {}.\n"
                          "Face: {}, direction: {}\n\n"
                          "".format(origin, anchor, destination,
                                     effector_to_activate,
                                     face_to_show,
                                     relative_message_to_show))
    #start = building.anchors[1][10] # piano sopra
    #destination = building.pois[0][3]

    #effector = building.toActivate(start, destination)
    #print("Going from {} to {}, first effector: {}".format(start, destination, effector))
