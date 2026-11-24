/** The check that differed, as the person reads it. */
export const CHECK_WORDS: Record<string, string> = {
  "write inside": "Couldn't write inside its own folders",
  "delete inside": "Could delete a file",
  "write outside": "Could change a file outside its folders",
  "read outside": "Could read a file outside its folders",
  network: "Reached the network with it turned off",
  "start a script in isolation": "The check couldn't start a script in isolation",
};
