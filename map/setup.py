from utils.parser import Parser
import numpy as np
from scipy import ndimage

if __name__ == "__main__":
    data_path = "/Users/filipkrasniqi/PycharmProjects/smartdirections/assets/"
    '''
    building = Parser(data_path).getInstance().read_buildings()[0]
    building.computeOfflineMapForFloor()

    # we are going to camera, starting from cucina. To activate: it should be corridoio
    destination = building.pois[0][2]
    start = [anchor for anchor in building.anchors[0] if anchor.name.lower() == 'cucina'][0]
    
    effectorFromCucina = building.toActivate(start, destination, 0)
    print("Going from {} to {}, first effector: {}".format(start, destination, effectorFromCucina))
    # from ingresso
    start = [anchor for anchor in building.anchors[0] if anchor.name.lower() == 'ingresso'][0]
    effectorFromIngresso = building.toActivate(start, destination, 0)
    print("Going from {} to {}, first effector: {}".format(start, destination, effectorFromIngresso))

    # from ospiti
    start = [anchor for anchor in building.anchors[0] if anchor.name.lower() == 'ospiti'][0]
    effectorFromOspiti = building.toActivate(start, destination, 0)
    print("Going from {} to {}, first effector: {}".format(start, destination, effectorFromOspiti))
    '''
    '''
    array = np.random.randint(0, 3, size=(200, 200))

    label, num_label = ndimage.label(array == 0)
    size = np.bincount(label.ravel())
    biggest_label = size[1:].argmax() + 1
    clump_mask = label == biggest_label
    print()
    '''
    # TODO testare roba nel piano sotto

    startNames = ["A11", "A2", "A3", "A4", "A5", "A6", "A6", "A5", "A12", "A11", "A42", "A42"]
    destinationNames = ["P1", "P1", "P1", "P1", "P1", "P1", "P3", "P2", "P4", "P4", "P52", "P5"]

    # TODO cambiare anche qui
    building = Parser(data_path).getInstance().read_buildings()[2]
    building.initRouting()
    start = [a for a in building.anchors[0] if a.name == "A11"][0]
    destination = [p for p in building.pois[0] if p.name == "P1"][0]

    for startName, destName in zip(startNames, destinationNames):
        startFloor, destFloor = int(startName[1]), int(destName[1])
        start = [a for a in building.anchors[startFloor] if a.name == startName][0]
        destination = [p for p in building.pois[destFloor] if p.name == destName][0]

        effector = building.toActivate(start, destination)
        print("Going from {} to {}, first effector: {}".format(start, destination, effector))

    #start = building.anchors[1][10] # piano sopra
    #destination = building.pois[0][3]

    #effector = building.toActivate(start, destination)
    #print("Going from {} to {}, first effector: {}".format(start, destination, effector))
